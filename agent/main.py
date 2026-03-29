from __future__ import annotations

from agent.managers import emotion_condition_manager
from agent.memory import memory_manager
from agent.orchestration.listen import listen
from agent.orchestration.memorize import memorize
from agent.orchestration.thinking import think
from agent.storage import graph_db_manager


def analyze_message(bot_id: str, user_id: str, user_input: str) -> str:
    """Process a user message through the listen → think → memorize pipeline.

    1. **Listen** – analyse the input and update the bot's emotions.
    2. **Think** – gather full context and generate ReAct + message.
    3. **Memorize** – reflect and update emotion conditions / world views.
    """
    db = graph_db_manager.load()
    bot_name = db.get_bot_name(bot_id) or "Bot"
    traits = db.get_bot_traits(bot_id)
    current_emotions = db.get_bot_emotions(bot_id)
    recent_chats = memory_manager.get_latest_n_chat(bot_id, n=5)

    # ── Phase 1: Listen ──────────────────────────────────────
    new_emotions = listen(
        user_input,
        bot_id,
        bot_name=bot_name,
        traits=traits,
        current_emotions=current_emotions,
        recent_chats=recent_chats,
    )

    # ── Phase 2: Think ───────────────────────────────────────
    thinking_result = think(
        user_input=user_input,
        bot_id=bot_id,
        bot_name=bot_name,
        traits=traits,
        current_emotions=new_emotions,
        recent_chats=recent_chats,
    )

    # ── Phase 3: Memorize ────────────────────────────────────
    world_views = db.get_world_views(bot_id)
    emotion_conditions = emotion_condition_manager.get_emotion_conditions(bot_id)

    memorize(
        bot_id=bot_id,
        bot_name=bot_name,
        user_id=user_id,
        user_input=user_input,
        react=thinking_result["react"],
        message=thinking_result["message"],
        new_emotions=new_emotions,
        recent_chats=recent_chats,
        world_views=world_views,
        emotion_conditions=emotion_conditions,
    )

    return thinking_result["message"]
