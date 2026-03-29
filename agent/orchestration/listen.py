from __future__ import annotations

from typing import Dict, List, Tuple

from langgraph import StateGraph
from langgraph.graph import END

from agent.managers import traits_manager
from agent.memory import memory_manager
from agent.storage import graph_db_manager
from agent.utils import llm


class ListenState:
    user_input: str
    bot_id: str
    traits: Dict[str, float]
    current_emotions: Dict[str, float]
    recent_chats: List[Dict[str, str]]
    new_emotions: Dict[str, Tuple[float, str]] | None = None


def retrieve_context(state: ListenState) -> ListenState:
    """Retrieve traits, emotions, and recent chats."""
    state.traits = traits_manager.get_bot_traits(state.bot_id)
    state.current_emotions = graph_db_manager.load().get_bot_emotions(state.bot_id)
    state.recent_chats = memory_manager.get_latest_n_chat(
        state.bot_id, 5
    )  # Assuming n=5
    return state


def analyze_and_update_emotions(state: ListenState) -> ListenState:
    """Use LLM to analyze and propose new emotion weights."""
    prompt = f"""
    Analyze the user's input in the context of the bot's traits, current emotions, and recent chats.
    Update the bot's emotions based on the analysis. For each emotion, provide a new value (0-1) and a short reason explaining the change based on the story/traits/input.

    User Input: {state.user_input}
    Traits: {state.traits}
    Current Emotions: {state.current_emotions}
    Recent Chats: {state.recent_chats}

    Output only a valid Python dictionary of emotions, e.g., {{"happiness": [0.5, "reduced from 0.8 because the user talked about a scary movie, conflicting with the bot's trait of not liking horror"], "sadness": [0.3, "increased due to empathetic response"]}}
    """

    response = llm.generate(prompt)
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
            state.new_emotions = new_emotions
        else:
            raise ValueError("Invalid emotion format")
    except Exception as e:
        print(f"Error parsing LLM response: {e}. Using current emotions.")
        state.new_emotions = {
            k: (v, "No change") for k, v in state.current_emotions.items()
        }
    return state


def update_graph(state: ListenState) -> ListenState:
    """Update the graph with new emotions."""
    if state.new_emotions:
        db = graph_db_manager.load()
        for emotion_name, (weight, reason) in state.new_emotions.items():
            db.update_bot_emotion(state.bot_id, emotion_name, weight, reason)
    return state


def listen(user_input: str, bot_id: str) -> None:
    """Process user input and update bot emotions using LangGraph."""
    graph = StateGraph(ListenState)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("analyze", analyze_and_update_emotions)
    graph.add_node("update", update_graph)

    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "update")
    graph.add_edge("update", END)

    graph.set_entry_point("retrieve")

    app = graph.compile()

    initial_state = ListenState(
        user_input=user_input,
        bot_id=bot_id,
        traits={},
        current_emotions={},
        recent_chats=[],
        new_emotions=None,
    )

    app.invoke(initial_state)
