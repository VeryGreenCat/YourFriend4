"""Extract bot personality traits and emotion conditions from a traits description."""
from __future__ import annotations

import json
import re
from typing import Any

from agent.utils.config import get_config
from agent.utils.llm import chat_completion
from agent.utils.constants import TRAIT_NODES, EMOTIONS


def extract_traits_and_conditions(
    traits_text: str,
) -> tuple[dict[str, float], list[dict[str, Any]], dict[str, float]]:
    """Analyse *traits_text* with an LLM and return structured data.

    Returns
    -------
    traits : dict[str, float]
        Personality trait name → weight in [-1, 1].
    emotion_conditions : list[dict]
        Each dict has ``description`` (str) and optional ``reason`` (str | None).
    emotions : dict[str, float]
        Baseline emotion name → weight in [0, 1].
    """
    cfg = get_config()
    trait_names = list(TRAIT_NODES.keys())
    emotion_names = [e[0] for e in EMOTIONS]

    system_prompt = (
        "You are a personality analyzer. Given a bot character's traits description, extract:\n"
        "1. traits: Personality trait scores.\n"
        f"   Keys from: {json.dumps(trait_names)}\n"
        "   Values: float in [-1, 1]. -1 = very low, 0 = neutral, 1 = very high.\n\n"
        "2. emotion_conditions: Specific emotional triggers or conditions.\n"
        '   Each has a "description" (e.g. "Afraid of confined spaces") and optional "reason" (why).\n\n'
        "3. emotions: Baseline emotion levels.\n"
        f"   Keys from: {json.dumps(emotion_names)}\n"
        "   Values: float in [0, 1]. 0 = not present, 1 = very strong baseline.\n\n"
        "Return strictly valid JSON:\n"
        '{"traits": {"kindness": 0.8, ...}, '
        '"emotion_conditions": [{"description": "...", "reason": "..."}], '
        '"emotions": {"happiness": 0.6, ...}}\n'
        "Only include traits/emotions that are relevant. Return ONLY JSON, no extra text."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Character traits:\n{traits_text}"},
    ]
    content = chat_completion(cfg.traits_llm_model, messages, temperature=0)

    # If parsing fails below, we will log the raw model output for debugging
    def _log_failure(name: str, model: str, prompt_messages, output: str) -> None:
        try:
            import datetime, os
            os.makedirs("logs", exist_ok=True)
            path = os.path.join("logs", "extractor_failures.log")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"\n---\n{datetime.datetime.utcnow().isoformat()}Z | {name} | model={model}\n")
                fh.write("MESSAGES:\n")
                fh.write(str(prompt_messages))
                fh.write("\nOUTPUT:\n")
                fh.write(output)
                fh.write("\n---\n")
        except Exception:
            pass

    data: dict | None = None
    try:
        data = json.loads(content)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                # log raw output for debugging
                _log_failure("bot_traits_extractor", cfg.traits_llm_model, messages, content)
                pass
        else:
            _log_failure("bot_traits_extractor", cfg.traits_llm_model, messages, content)
    if not isinstance(data, dict):
        data = {}

    # ── parse traits ──
    valid_traits = set(TRAIT_NODES.keys())
    traits: dict[str, float] = {}
    for k, v in data.get("traits", {}).items():
        if k in valid_traits:
            try:
                v = max(-1.0, min(1.0, float(v)))
            except (TypeError, ValueError):
                v = 0.0
            traits[k] = v

    # ── parse emotion conditions ──
    conditions: list[dict[str, Any]] = []
    for ec in data.get("emotion_conditions", []):
        if isinstance(ec, dict) and "description" in ec:
            conditions.append(
                {"description": str(ec["description"]), "reason": ec.get("reason")}
            )

    # ── parse emotions ──
    valid_emotions = set([e[0] for e in EMOTIONS])
    emotions: dict[str, float] = {}
    for k, v in data.get("emotions", {}).items():
        if k in valid_emotions:
            try:
                v = max(0.0, min(1.0, float(v)))
            except (TypeError, ValueError):
                v = 0.0
            emotions[k] = v

    return traits, conditions, emotions
