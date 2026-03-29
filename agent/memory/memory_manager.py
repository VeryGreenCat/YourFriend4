from __future__ import annotations

from agent.storage import graph_db_manager, supa_db_manager


def get_latest_n_chat(bot_id: str, n: int) -> list[dict]:
    """Return the latest *n* chat messages for the given bot."""
    return supa_db_manager.get_latest_n_chat(bot_id, n)


def get_bot_summary(bot_id: str) -> str | None:
    """Return the bot's condensed memory summary text, or None if not set."""
    db = graph_db_manager.load()
    text, _ = db.get_bot_summary(bot_id)
    return text
