from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agent.managers import rag_manager
from agent.memory import memory_manager
from agent.storage import graph_db_manager
from agent.utils import llm
from agent.utils.config import get_config


class ThinkingResult(TypedDict):
    react: str  # 3rd-person internal reasoning
    message: str  # 1st-person bot reply


class ThinkingState(TypedDict):
    user_input: str
    bot_id: str
    bot_name: str
    traits: Dict[str, float]
    current_emotions: Dict[str, Any]  # {"emotion": {"weight": float, "reason": str}}
    recent_chats: List[Dict[str, str]]
    world_views: List[Dict]
    memory_summary: Optional[str]
    backstory_chunks: List[str]
    react: str  # 3rd-person reasoning about how to respond
    response: str  # 1st-person message the bot will say


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
    """Produce a ReAct reasoning (3rd person) and the bot's reply (1st person)."""
    import time as _time

    cfg = get_config()
    bot_name = state["bot_name"]
    unix_time = int(_time.time())

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
        f"You are simulating the internal thought process and reply of a bot named '{bot_name}'.\n"
        "Use the bot's traits, emotional state, worldviews, memories, and backstory.\n\n"
        "You MUST output EXACTLY a JSON array with two strings:\n"
        "  1. ReAct — 3rd-person reasoning describing what the bot thinks/feels and how it decides to respond.\n"
        "  2. Message — the 1st-person message the bot will actually say to the user.\n\n"
        'Example: ["ตอบแบบโกรธ เพราะว่าผู้ใช้พูดจาไม่ดี", "อย่ามายุ่ง"]\n\n'
        "Output ONLY the JSON array — no extra text, no markdown fences."
    )

    user_prompt = f"""Bot Name: {bot_name}
Current Unix Time: {unix_time}

User's message: {state["user_input"]}

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

=== Output (JSON array: [react, message]) ==="""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = llm.chat_completion(cfg.traits_llm_model, messages, temperature=0.7)

    import json as _json

    try:
        parsed = _json.loads(raw)
        if isinstance(parsed, list) and len(parsed) == 2:
            react, response = parsed[0], parsed[1]
        else:
            react, response = raw, raw
    except (_json.JSONDecodeError, ValueError):
        react, response = raw, raw

    return {**state, "react": react, "response": response}


# ── Public entry point ────────────────────────────────────────────────────────


def think(
    user_input: str,
    bot_id: str,
    bot_name: str,
    traits: Dict[str, float],
    current_emotions: Dict[str, Any],
    recent_chats: List[Dict[str, str]],
) -> ThinkingResult:
    """Run the thinking pipeline and return the bot's ReAct reasoning + message.

    Args:
        user_input:       The user's latest message.
        bot_id:           The bot's unique identifier.
        traits:           Bot personality traits {name: weight}.
        current_emotions: Bot's current emotional state
                          {name: {"weight": float, "reason": str}}.
        recent_chats:     Recent conversation history [{role, content}, ...].

    Returns:
        ThinkingResult with ``react`` (3rd-person reasoning) and ``message``
        (1st-person bot reply).
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
        "bot_name": bot_name,
        "traits": traits,
        "current_emotions": current_emotions,
        "recent_chats": recent_chats,
        "world_views": [],
        "memory_summary": None,
        "backstory_chunks": [],
        "react": "",
        "response": "",
    }

    result = app.invoke(initial_state)
    return ThinkingResult(react=result["react"], message=result["response"])
