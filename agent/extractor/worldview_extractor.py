"""Extract world views from a bot's backstory using an LLM."""
from __future__ import annotations

import json
import re
from typing import Any

from agent.utils.config import get_config
from agent.utils.llm import chat_completion
from agent.utils.constants import TRAIT_NODES


def extract_world_views(backstory: str) -> list[dict[str, Any]]:
    """Return a list of world-view dicts extracted from *backstory*.

    Each dict contains:
    - ``description``      – world-view statement
    - ``affected_traits``  – list of ``{"name": <trait>, "change_per_second": <float>}``
    - ``reason``           – why the character holds this view (or *None*)
    """
    cfg = get_config()
    trait_names = list(TRAIT_NODES.keys())

    system_prompt = (
        "You are a character analyst. Given a character's backstory, extract their world views.\n"
        "A world view is a fundamental belief or perspective about the world that shapes behaviour over time.\n\n"
        "For each world view, identify:\n"
        "1. description: A clear description of the world view\n"
        "2. affected_traits: Which personality traits this world view gradually influences, "
        "and at what rate (change_per_second as a very small float, e.g. 0.0000001 for slow "
        "real-time change). Positive = increase, negative = decrease.\n"
        "3. reason: Why the character holds this world view (from their backstory), or null\n\n"
        f"Available traits: {json.dumps(trait_names)}\n\n"
        "Return strictly valid JSON array. Example:\n"
        '[\n'
        '  {\n'
        '    "description": "Believes the world is fundamentally unfair",\n'
        '    "affected_traits": [\n'
        '      {"name": "optimism", "change_per_second": -0.0000001},\n'
        '      {"name": "aggressiveness", "change_per_second": 0.00000005}\n'
        '    ],\n'
        '    "reason": "Grew up in poverty and was denied opportunities"\n'
        '  }\n'
        ']\n\n'
        "If no world views can be extracted, return an empty array [].\n"
        "Return ONLY the JSON array, no extra text."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Backstory:\n{backstory}"},
    ]
    content = chat_completion(cfg.traits_llm_model, messages, temperature=0)

    # log failures when parsing the model output
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

    data: list | None = None
    try:
        data = json.loads(content)
    except Exception:
        m = re.search(r"\[[\s\S]*\]", content)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                _log_failure("worldview_extractor", cfg.traits_llm_model, messages, content)
                pass
        else:
            _log_failure("worldview_extractor", cfg.traits_llm_model, messages, content)
    if not isinstance(data, list):
        return []

    valid_traits = set(TRAIT_NODES.keys())
    results: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or "description" not in item:
            continue
        affected: list[dict[str, Any]] = []
        for t in item.get("affected_traits", []):
            if isinstance(t, dict) and t.get("name") in valid_traits:
                affected.append(
                    {
                        "name": t["name"],
                        "change_per_second": float(t.get("change_per_second", 0)),
                    }
                )
        results.append(
            {
                "description": str(item["description"]),
                "affected_traits": affected,
                "reason": item.get("reason"),
            }
        )
    return results
