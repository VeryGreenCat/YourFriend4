"""Memorize pipeline — reflect on the bot's response and decide whether to
update emotion conditions and/or world views.

Inputs (from the thinking layer):
  - react        : 3rd-person reasoning about why the bot responded this way
  - message      : 1st-person message the bot said
  - recent_chats : recent conversation history
  - world_views  : current world views
  - emotion_conditions : current emotion conditions
  - bot_id

LangGraph flow:
  decide_updates  →  apply_updates  →  END
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agent.managers import emotion_condition_manager, worldview_manager
from agent.storage import graph_db_manager, supa_db_manager
from agent.utils import llm
from agent.utils.config import get_config


class MemorizeState(TypedDict):
    bot_id: str
    bot_name: str
    user_id: str
    user_input: str
    react: str
    message: str
    new_emotions: Dict[str, Any]  # {name: {"weight": float, "reason": str}}
    recent_chats: List[Dict[str, str]]
    world_views: List[Dict]
    emotion_conditions: List[Dict]
    plan: Optional[Dict[str, Any]]  # LLM decision payload


# ── Graph nodes ───────────────────────────────────────────────────────────────


def decide_updates(state: MemorizeState) -> MemorizeState:
    """Ask the LLM what (if anything) should change in emotion conditions
    and world views based on the latest interaction."""
    import time as _time

    cfg = get_config()
    bot_name = state["bot_name"]
    unix_time = int(_time.time())

    wv_lines = []
    for wv in state["world_views"]:
        wv_lines.append(f'  - id: {wv["id"]}, description: {wv.get("description", "")}')
    wv_text = "\n".join(wv_lines) or "  (none)"

    ec_lines = []
    for ec in state["emotion_conditions"]:
        ec_lines.append(f'  - id: {ec["id"]}, description: {ec.get("description", "")}')
    ec_text = "\n".join(ec_lines) or "  (none)"

    chat_lines = []
    for msg in state["recent_chats"]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        chat_lines.append(f"  [{role}]: {content}")
    chats_text = "\n".join(chat_lines) or "  (none)"

    system_prompt = (
        f"You are an internal reflection engine for a simulated bot named '{bot_name}'.\n"
        "Given the bot's latest ReAct reasoning, the message it said, recent chat, "
        "its current emotion conditions, and world views, decide what updates are needed.\n\n"
        "For EACH of emotion_conditions and world_views you can:\n"
        '  - "add"    : create a new entry  (provide description and optional reason)\n'
        '  - "update" : edit an existing entry (provide id, new description, optional reason)\n'
        '  - "remove" : delete an existing entry (provide id)\n'
        "  - or do nothing (omit from the list)\n\n"
        "Output ONLY valid JSON with this schema (no markdown fences):\n"
        "{\n"
        '  "emotion_conditions": [\n'
        '    {"action": "add", "description": "...", "reason": "..."},\n'
        '    {"action": "update", "id": "...", "description": "...", "reason": "..."},\n'
        '    {"action": "remove", "id": "..."}\n'
        "  ],\n"
        '  "world_views": [\n'
        '    {"action": "add", "description": "...", "affected_traits": [{"name": "...", "change_per_second": 0.01}], "reason": "..."},\n'
        '    {"action": "update", "id": "...", "description": "...", "affected_traits": [...], "reason": "..."},\n'
        '    {"action": "remove", "id": "..."}\n'
        "  ]\n"
        "}\n"
        "If no changes are needed for a category, use an empty list []."
    )

    user_prompt = f"""Bot Name: {bot_name}
Current Unix Time: {unix_time}

=== Bot's Internal Reasoning (ReAct, 3rd person) ===
{state["react"]}

=== Bot's Message (1st person) ===
{state["message"]}

=== Recent Conversation ===
{chats_text}

=== Current Emotion Conditions ===
{ec_text}

=== Current World Views ===
{wv_text}

=== Your Decision (JSON) ==="""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = llm.chat_completion(cfg.traits_llm_model, messages, temperature=0.3)

    try:
        plan = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        plan = {"emotion_conditions": [], "world_views": []}

    return {**state, "plan": plan}


def apply_updates(state: MemorizeState) -> MemorizeState:
    """Execute the planned add / update / remove operations."""
    plan = state.get("plan") or {}
    bot_id = state["bot_id"]

    # ── Emotion Conditions ────────────────────────────────────
    for op in plan.get("emotion_conditions", []):
        action = op.get("action")
        if action == "add":
            ec_id = str(uuid.uuid4())
            db = graph_db_manager.load()
            db.create_emotion_condition(
                bot_id, ec_id, op["description"], op.get("reason")
            )
        elif action == "update" and op.get("id"):
            emotion_condition_manager.update_emotion_condition(
                op["id"], op["description"], op.get("reason")
            )
        elif action == "remove" and op.get("id"):
            emotion_condition_manager.remove_emotion_condition(op["id"])

    # ── World Views ───────────────────────────────────────────
    for op in plan.get("world_views", []):
        action = op.get("action")
        if action == "add":
            wv_id = str(uuid.uuid4())
            db = graph_db_manager.load()
            db.create_world_view(
                bot_id,
                wv_id,
                op["description"],
                op.get("affected_traits", []),
                op.get("reason"),
            )
        elif action == "update" and op.get("id"):
            worldview_manager.update_world_view(
                op["id"],
                op["description"],
                op.get("affected_traits", []),
                op.get("reason"),
            )
        elif action == "remove" and op.get("id"):
            worldview_manager.remove_world_view(op["id"])

    return state


def save_chat_history(state: MemorizeState) -> MemorizeState:
    """Save both user and bot messages to Supabase ChatHistory.

    The snapshot field stores the current emotion weights and reasons from
    the graph DB as a JSON string.
    """
    snapshot = json.dumps(state["new_emotions"], ensure_ascii=False)

    # Save user message
    supa_db_manager.add_chat_history(
        user_id=state["user_id"],
        bot_id=state["bot_id"],
        content=state["user_input"],
        snapshot="",
        author="user",
    )

    # Save bot response
    supa_db_manager.add_chat_history(
        user_id=state["user_id"],
        bot_id=state["bot_id"],
        content=state["message"],
        snapshot=snapshot,
        author="bot",
    )

    return state


# ── Public entry point ────────────────────────────────────────────────────────


def memorize(
    bot_id: str,
    bot_name: str,
    user_id: str,
    user_input: str,
    react: str,
    message: str,
    new_emotions: Dict[str, Any],
    recent_chats: List[Dict[str, str]],
    world_views: List[Dict],
    emotion_conditions: List[Dict],
) -> None:
    """Reflect on the latest interaction and update emotion conditions /
    world views as needed.

    This is the post-response reflection step.
    """
    graph = StateGraph(MemorizeState)
    graph.add_node("decide_updates", decide_updates)
    graph.add_node("apply_updates", apply_updates)
    graph.add_node("save_chat_history", save_chat_history)

    graph.set_entry_point("decide_updates")
    graph.add_edge("decide_updates", "apply_updates")
    graph.add_edge("apply_updates", "save_chat_history")
    graph.add_edge("save_chat_history", END)

    app = graph.compile()

    initial_state: MemorizeState = {
        "bot_id": bot_id,
        "bot_name": bot_name,
        "user_id": user_id,
        "user_input": user_input,
        "new_emotions": new_emotions,
        "react": react,
        "message": message,
        "recent_chats": recent_chats,
        "world_views": world_views,
        "emotion_conditions": emotion_conditions,
        "plan": None,
    }

    app.invoke(initial_state)
