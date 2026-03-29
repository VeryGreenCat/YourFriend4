import os
import json
import re
from typing import Dict

from agent.utils.config import get_config
from agent.utils.llm import chat_completion

_model = None

# emotions: main->happiness, sadness, fear, disgust, anger, and surprise
# sub_emotions: 
# Admiration: Respect for someone.
# Adoration: Deep love and admiration.
# Aesthetic appreciation: Appreciation of beauty.
# Amusement: Finding something funny.
# Anger: Strong annoyance or displeasure.
# Anxiety: Worry or unease.
# Awe: Wonder or admiration.
# Awkwardness: Social discomfort.
# Boredom: Lack of interest.
# Calmness: Tranquility.
# Confusion: Lack of understanding.
# Craving: Strong desire.
# Disgust: Intense dislike.
# Empathic pain: Feeling others' suffering.
# Entrancement: Being mesmerized.
# Excitement: Great enthusiasm.
# Fear: Unpleasant emotion caused by threat.
# Horror: Intense fear or shock.
# Interest: Curiosity or concern.
# Joy: Great pleasure.
# Nostalgia: Sentimental longing.
# Relief: Alleviation of distress.
# Romance: Romantic love.
# Sadness: Unhappiness.
# Satisfaction: Fulfillment.
# Sexual desire: Physical longing.
# Surprise: Astonishment.

class TraitsModel:
    # Personality + emotion-aligned traits. Scores in [-1,1].
    TRAITS = [
        # personality dimensions
        "kindness",
        "aggressiveness",
        "rationality",
        "emotional_stability",
        "honesty",
        "optimism",
        # primary emotion axes (mapped to trait-style scores)
        "happiness",
        "sadness",
        "fear",
        "disgust",
        "anger",
        "surprise",
        # supporting affective traits
        "calmness",
        "anxiety",
        "empathy",
        "curiosity",
    ]

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        self.model_name = model_name or os.getenv("TRAITS_LLM_MODEL", "gpt-4o-mini")

    def _build_system_prompt(self) -> str:
        return (
            "You are a personality analyzer. Given a short character description, "
            "output ONLY a JSON object with these keys: kindness, aggressiveness, rationality, "
            "emotional_stability, honesty, optimism, happiness, sadness, fear, disgust, anger, surprise, "
            "calmness, anxiety, empathy, curiosity.\n"
            "Each value must be a number between -1 and 1 (inclusive): -1 = very low, 0 = neutral, 1 = very high.\n"
            "Be deterministic and consistent. Use temperature 0. Return strictly valid JSON with no extra text.\n"
            "Trait definitions:\n"
            "- kindness: caring vs cruel\n"
            "- aggressiveness: passive vs hostile\n"
            "- rationality: emotional vs logical\n"
            "- emotional_stability: unstable vs calm\n"
            "- honesty: deceptive vs truthful\n"
            "- optimism: pessimistic vs optimistic\n"
            "- happiness: unhappy vs joyful\n"
            "- sadness: not sad vs sad\n"
            "- fear: fearless vs fearful\n"
            "- disgust: accepting vs disgusted\n"
            "- anger: calm vs angry\n"
            "- surprise: unsurprised vs surprised\n"
            "- calmness: agitated vs calm\n"
            "- anxiety: relaxed vs anxious\n"
            "- empathy: indifferent vs empathic\n"
            "- curiosity: uninterested vs curious\n"
        )

    def __call__(self, text: str) -> Dict[str, float]:
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"Character:\n{text}"},
        ]

        content = chat_completion(self.model_name, messages, temperature=0)

        data = None
        try:
            data = json.loads(content)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    data = None

        if not isinstance(data, dict):
            return {k: 0.0 for k in self.TRAITS}

        out: Dict[str, float] = {}
        for t in self.TRAITS:
            v = data.get(t, 0)
            try:
                v = float(v)
            except Exception:
                v = 0.0
            # clamp to [-1, 1]
            if v < -1:
                v = -1.0
            if v > 1:
                v = 1.0
            out[t] = v

        return out


def load():
    global _model
    if _model is None:
        cfg = get_config()
        model_name = cfg.traits_llm_model or None
        _model = TraitsModel(model_name=model_name)
    return _model
