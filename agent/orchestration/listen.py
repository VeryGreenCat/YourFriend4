from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import END, StateGraph

from agent.storage import graph_db_manager
from agent.utils import llm
from agent.utils.config import get_config


class ListenState(TypedDict):
    user_input: str
    bot_id: str
    bot_name: str
    traits: Dict[str, float]
    current_emotions: Dict[str, float]
    recent_chats: List[Dict[str, str]]
    new_emotions: Optional[Dict[str, Tuple[float, str]]]


def analyze_and_update_emotions(state: ListenState) -> ListenState:
    """Use LLM to analyze and propose new emotion weights."""
    import time as _time

    prompt = f"""
    Bot Name: {state["bot_name"]}
    Current Unix Time: {int(_time.time())}

    Analyze the user's input in the context of the bot's traits, current emotions, and recent chats.
    Update the bot's emotions based on the analysis. For each emotion, provide a new value (0-1) and a short reason explaining the change based on the story/traits/input.

    User Input: {state["user_input"]}
    Traits: {state["traits"]}
    Current Emotions: {state["current_emotions"]}
    Recent Chats: {state["recent_chats"]}

    Output only a valid Python dictionary of emotions, e.g., {{"happiness": [0.5, "reduced from 0.8 because the user talked about a scary movie, conflicting with the bot's trait of not liking horror"], "sadness": [0.3, "increased due to empathetic response"]}}
    """
    cfg = get_config()
    messages = [
        {
            "role": "system",
            "content": (
                "You are an emotion analysis engine. Analyze the user's input in the "
                "context of the bot's traits, current emotions, and recent chats. "
                "For each emotion, provide a new value (0-1) and a short reason. "
                "Output ONLY a valid Python dictionary, e.g., "
                '{"happiness": [0.5, "reason"], "sadness": [0.3, "reason"]}'
            ),
        },
        {"role": "user", "content": prompt},
    ]
    response = llm.chat_completion(cfg.traits_llm_model, messages, temperature=0.3)
    try:
        new_emotions_raw = eval(
            response.strip()
        )  # Simple eval, in production use safer parsing
        if isinstance(new_emotions_raw, dict):
            new_emotions = {}
            for emotion, data in new_emotions_raw.items():
                if (
                    isinstance(data, list)
                    and len(data) == 2
                    and isinstance(data[0], (int, float))
                    and 0 <= data[0] <= 1
                    and isinstance(data[1], str)
                ):
                    new_emotions[emotion] = (data[0], data[1])
                else:
                    raise ValueError(f"Invalid format for emotion {emotion}")
            return {**state, "new_emotions": new_emotions}
        else:
            raise ValueError("Invalid emotion format")
    except Exception as e:
        print(f"Error parsing LLM response: {e}. Using current emotions.")
        fallback = {k: (v, "No change") for k, v in state["current_emotions"].items()}
        return {**state, "new_emotions": fallback}


def update_graph(state: ListenState) -> ListenState:
    """Update the graph with new emotions."""
    new_emotions = state.get("new_emotions")
    if new_emotions:
        db = graph_db_manager.load()
        for emotion_name, (weight, reason) in new_emotions.items():
            db.update_bot_emotion(state["bot_id"], emotion_name, weight, reason)
    return state


def listen(
    user_input: str,
    bot_id: str,
    bot_name: str,
    traits: Dict[str, float],
    current_emotions: Dict[str, float],
    recent_chats: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Process user input, update bot emotions, and return the new emotion state.

    Returns:
        Dict mapping emotion names to {"weight": float, "reason": str}.
    """
    graph = StateGraph(ListenState)
    graph.add_node("analyze", analyze_and_update_emotions)
    graph.add_node("update", update_graph)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "update")
    graph.add_edge("update", END)

    app = graph.compile()

    initial_state: ListenState = {
        "user_input": user_input,
        "bot_id": bot_id,
        "bot_name": bot_name,
        "traits": traits,
        "current_emotions": current_emotions,
        "recent_chats": recent_chats,
        "new_emotions": None,
    }

    result = app.invoke(initial_state)

    # Convert (weight, reason) tuples into dicts for the thinking layer
    new_emotions = result.get("new_emotions") or {}
    return {
        name: {"weight": weight, "reason": reason}
        for name, (weight, reason) in new_emotions.items()
    }
