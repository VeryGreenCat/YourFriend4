import json
from typing import Any, Dict, List

from agent.utils.config import get_config
from agent.utils.llm import chat_completion
from agent.utils.logger import log_failure


def predict_text_emotion(content: str) -> List[Dict[str, Any]]:
    """Return list[{'label': str, 'score': float}] for `content`.

    If LLM backend configured (openai/ollama) use `agent.utils.llm.chat_completion`
    to ask the model to return a JSON array of label/score objects. Otherwise
    fall back to HF pipeline.
    """
    cfg = get_config()
    backend = (cfg.llm_backend or "").lower()
    if backend in ("openai", "ollama"):
        # ask the LLM to return a JSON array like [{"label":"joy","score":0.8}, ...]
        system = (
            "You are an emotion classifier. Given a text, return a JSON array of"
            " objects with keys 'label' and 'score' (0.0-1.0). Return only JSON."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Classify emotions in the text:\n{content}"},
        ]
        resp = chat_completion(cfg.traits_llm_model, messages, temperature=0)
        try:
            data = json.loads(resp)
            if isinstance(data, list):
                out: List[Dict[str, Any]] = []
                for item in data:
                    if isinstance(item, dict) and "label" in item:
                        out.append({"label": item["label"], "score": float(item.get("score", 0))})
                return out
        except Exception:
            log_failure("emotion_extractor", cfg.traits_llm_model, messages, str(resp))
        # fallthrough to empty
        return []

    # Do not fall back to HuggingFace models anymore; if no chat LLM is
    # configured, return an empty result so callers handle it uniformly.
    return []

