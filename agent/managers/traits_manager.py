"""Manage Bot ↔ Trait relationships in the graph database."""
from __future__ import annotations

from agent.extractor.bot_traits_extractor import extract_traits_and_conditions
from agent.storage import graph_db_manager


def update_bot_traits(bot_id: str, traits_text: str):
    """Extract traits from *traits_text* and persist Bot→Trait / Bot→Emotion edges.

    Returns
    -------
    traits : dict[str, float]
    conditions : list[dict]
    emotions : dict[str, float]
    """
    traits, conditions, emotions = extract_traits_and_conditions(traits_text)

    db = graph_db_manager.load()

    db.clear_bot_traits(bot_id)
    for trait_name, weight in traits.items():
        db.link_bot_trait(bot_id, trait_name, weight)

    db.clear_bot_emotions(bot_id)
    for emotion_name, weight in emotions.items():
        db.link_bot_emotion(bot_id, emotion_name, weight)

    return traits, conditions, emotions
