from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agent.managers import rag_manager
from agent.memory import memory_manager
from agent.storage import graph_db_manager
from agent.utils import llm
from agent.utils.config import get_config


class ThinkingState(TypedDict):
    user_input: str
    bot_id: str
    traits: Dict[str, float]
    current_emotions: Dict[str, Any]  # {"emotion": {"weight": float, "reason": str}}
    recent_chats: List[Dict[str, str]]
    world_views: List[Dict]
    memory_summary: Optional[str]
    backstory_chunks: List[str]
    response: str


# ── Graph nodes ───────────────────────────────────────────────────────────────


def pull_world_views(state: ThinkingState) -> ThinkingState:
    """Pull all WorldView nodes for the bot from the graph DB."""
    db = graph_db_manager.load()
    return {**state, "world_views": db.get_world_views(state["bot_id"])}


def pull_rag_memory(state: ThinkingState) -> ThinkingState:
    """Pull bot summary memory + relevant backstory chunks via RAG."""
    summary = memory_manager.get_bot_summary(state["bot_id"])
    chunks = rag_manager.search_backstory(state["bot_id"], state["user_input"])
    return {**state, "memory_summary": summary, "backstory_chunks": chunks}


def generate_response(state: ThinkingState) -> ThinkingState:
    """Synthesize all context and generate the bot's simulated response."""
    cfg = get_config()

    traits_text = (
        "\n".join(f"  - {k}: {v:.2f}" for k, v in state["traits"].items()) or "  (none)"
    )

    emotion_lines = []
    for name, data in state["current_emotions"].items():
        if isinstance(data, dict):
            weight = data.get("weight", 0)
            reason = data.get("reason", "")
        elif isinstance(data, (list, tuple)) and len(data) == 2:
            weight, reason = data
        else:
            weight, reason = data, ""
        emotion_lines.append(f"  - {name}: {weight:.2f}  ({reason})")
    emotions_text = "\n".join(emotion_lines) or "  (none)"

    chat_lines = []
    for msg in state["recent_chats"]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        chat_lines.append(f"  [{role}]: {content}")
    chats_text = "\n".join(chat_lines) or "  (none)"

    wv_lines = []
    for wv in state.get("world_views", []):
        desc = wv.get("description", "")
        reason = wv.get("reason") or ""
        wv_lines.append(f"  - {desc}" + (f"  (reason: {reason})" if reason else ""))
    world_views_text = "\n".join(wv_lines) or "  (none)"

    backstory_text = (
        "\n".join(
            f"  [{i + 1}] {chunk}"
            for i, chunk in enumerate(state.get("backstory_chunks", []))
        )
        or "  (none)"
    )

    summary_text = state.get("memory_summary") or "(no summary available)"

    system_prompt = (
        "You are simulating a bot's authentic reply to the user.\n"
        "Use the bot's traits, emotional state, worldviews, memories, and backstory "
        "to produce a response that feels natural and consistent with its personality.\n"
        "Reply ONLY with the bot's message — no meta-commentary, no explanations."
    )

    user_prompt = f"""User's message: {state["user_input"]}

=== Bot Context ===

Traits:
{traits_text}

Current Emotions (name: weight  reason):
{emotions_text}

Recent Conversation:
{chats_text}

Worldviews:
{world_views_text}

Summary Memory:
{summary_text}

Relevant Backstory Chunks:
{backstory_text}

=== Bot's Response ==="""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.chat_completion(cfg.traits_llm_model, messages, temperature=0.7)
    return {**state, "response": response}


# ── Public entry point ────────────────────────────────────────────────────────


def think(
    user_input: str,
    bot_id: str,
    traits: Dict[str, float],
    current_emotions: Dict[str, Any],
    recent_chats: List[Dict[str, str]],
) -> str:
    """Run the thinking pipeline and return the bot's simulated response.

    Args:
        user_input:       The user's latest message.
        bot_id:           The bot's unique identifier.
        traits:           Bot personality traits {name: weight}.
        current_emotions: Bot's current emotional state
                          {name: {"weight": float, "reason": str}}.
        recent_chats:     Recent conversation history [{role, content}, ...].

    Returns:
        The simulated bot response string.
    """
    graph = StateGraph(ThinkingState)
    graph.add_node("pull_world_views", pull_world_views)
    graph.add_node("pull_rag_memory", pull_rag_memory)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("pull_world_views")
    graph.add_edge("pull_world_views", "pull_rag_memory")
    graph.add_edge("pull_rag_memory", "generate_response")
    graph.add_edge("generate_response", END)

    app = graph.compile()

    initial_state: ThinkingState = {
        "user_input": user_input,
        "bot_id": bot_id,
        "traits": traits,
        "current_emotions": current_emotions,
        "recent_chats": recent_chats,
        "world_views": [],
        "memory_summary": None,
        "backstory_chunks": [],
        "response": "",
    }

    result = app.invoke(initial_state)
    return result["response"]
