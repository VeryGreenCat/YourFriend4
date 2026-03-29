"""Manage EmotionCondition nodes for bots in the graph database."""
from __future__ import annotations

import uuid

from agent.storage import graph_db_manager


def create_emotion_conditions(bot_id: str, conditions: list[dict]) -> None:
    """Clear existing conditions for *bot_id* and create new ones.

    Parameters
    ----------
    conditions : list[dict]
        Each dict must have ``description`` (str) and optional ``reason`` (str | None).
    """
    db = graph_db_manager.load()
    db.clear_emotion_conditions(bot_id)

    for cond in conditions:
        ec_id = str(uuid.uuid4())
        db.create_emotion_condition(
            bot_id, ec_id, cond["description"], cond.get("reason")
        )


def update_emotion_condition(ec_id: str, description: str, reason: str | None = None) -> None:
    db = graph_db_manager.load()
    db.update_emotion_condition(ec_id, description, reason)


def remove_emotion_condition(ec_id: str) -> None:
    db = graph_db_manager.load()
    db.remove_emotion_condition(ec_id)


def get_emotion_conditions(bot_id: str) -> list[dict]:
    db = graph_db_manager.load()
    return db.get_emotion_conditions(bot_id)
