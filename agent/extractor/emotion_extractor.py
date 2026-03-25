import pathlib
from typing import Any, Dict, List

from agent.utils.config import get_config

_model = None

def _download_hf_classification(model_id: str, local_dir: str) -> None:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    AutoTokenizer.from_pretrained(model_id).save_pretrained(local_dir)
    AutoModelForSequenceClassification.from_pretrained(model_id).save_pretrained(local_dir)

def load() -> Any:
    global _model

    if _model is not None:
        return _model
    try:
        from transformers import pipeline as hf_pipeline
    except Exception as e:
        raise RuntimeError(
            "transformers is required to load the text emotion model"
        ) from e

    cfg = get_config()
    model_path = pathlib.Path(cfg.text_emotion_model_path)
    if not model_path.exists():
        _download_hf_classification("cirimus/modernbert-base-go-emotions", str(model_path))
    _model = hf_pipeline(
        "text-classification",
        model=str(model_path),
        top_k=cfg.text_emotion_model_top_k,
    )
    return _model


def predict_text_emotion(content: str) -> List[Dict[str, Any]]:
    model = load()
    return model(content)

