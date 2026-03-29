from __future__ import annotations

from agent.managers import traits_manager
from agent.memory import memory_manager
from agent.orchestration.listen import listen
from agent.orchestration.thinking import think
from agent.storage import graph_db_manager


def analyze_message(bot_id: str, user_id: str, user_input: str) -> str:
    """Process a user message through the listen → think pipeline.

    1. **Listen** – analyse the input and update the bot's emotions.
    2. **Think** – gather full context and generate the bot's reply.
    """
    # ── Phase 1: Listen ──────────────────────────────────────
    listen(user_input, bot_id)

    # ── Phase 2: Gather updated context ──────────────────────
    db = graph_db_manager.load()
    traits = db.get_bot_traits(bot_id)
    current_emotions = db.get_bot_emotions(bot_id)
    recent_chats = memory_manager.get_latest_n_chat(bot_id, n=5)

    # ── Phase 3: Think ───────────────────────────────────────
    response = think(
        user_input=user_input,
        bot_id=bot_id,
        traits=traits,
        current_emotions=current_emotions,
        recent_chats=recent_chats,
    )

    return response
