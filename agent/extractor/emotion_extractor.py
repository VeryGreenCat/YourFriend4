import json
from typing import Any, Dict, List

from agent.utils.config import get_config
from agent.utils.llm import chat_completion


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
            # log failure
            try:
                import datetime, os
                os.makedirs("logs", exist_ok=True)
                with open(os.path.join("logs", "extractor_failures.log"), "a", encoding="utf-8") as fh:
                    fh.write(f"\n---\n{datetime.datetime.utcnow().isoformat()}Z | emotion_extractor | model={cfg.traits_llm_model}\nMESSAGES:\n")
                    fh.write(str(messages))
                    fh.write("\nOUTPUT:\n")
                    fh.write(str(resp))
                    fh.write("\n---\n")
            except Exception:
                pass
        # fallthrough to empty
        return []

    # Do not fall back to HuggingFace models anymore; if no chat LLM is
    # configured, return an empty result so callers handle it uniformly.
    return []

