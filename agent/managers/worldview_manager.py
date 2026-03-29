"""Manage WorldView nodes for bots in the graph database."""
from __future__ import annotations

import uuid
from typing import Any

from agent.extractor.worldview_extractor import extract_world_views
from agent.storage import graph_db_manager


def create_world_views_from_backstory(bot_id: str, backstory: str) -> list[dict[str, Any]]:
    """Extract world views from *backstory* via LLM and persist them.

    Returns the list of extracted world-view dicts.
    """
    world_views = extract_world_views(backstory)

    db = graph_db_manager.load()
    db.clear_world_views(bot_id)

    for wv in world_views:
        wv_id = str(uuid.uuid4())
        db.create_world_view(
            bot_id,
            wv_id,
            wv["description"],
            wv["affected_traits"],
            wv.get("reason"),
        )

    return world_views


def update_world_view(
    wv_id: str,
    description: str,
    affected_traits: list[dict],
    reason: str | None = None,
) -> None:
    db = graph_db_manager.load()
    db.update_world_view(wv_id, description, affected_traits, reason)


def remove_world_view(wv_id: str) -> None:
    db = graph_db_manager.load()
    db.remove_world_view(wv_id)


def get_world_views(bot_id: str) -> list[dict]:
    db = graph_db_manager.load()
    return db.get_world_views(bot_id)
