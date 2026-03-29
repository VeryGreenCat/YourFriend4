"""Adapter to convert extractor outputs into a Langraph-friendly payload.

This module uses the existing models to produce a simple graph payload
containing a `character` node and edges to `trait` and `emotion` nodes
with scores. It does not depend on a Langraph client — it returns a
serializable dict you can forward to your ingestion pipeline.
"""
from typing import Dict, List, Any

from agent.extractor.traits_extractor import load
from agent.extractor.emotion_extractor import predict_text_emotion


def create_langraph_payload(text: str, character_id: str | None = None) -> Dict[str, Any]:
    traits_model = load()
    traits = traits_model(text)
    emotions = predict_text_emotion(text)

    cid = character_id or "character:1"

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Character node
    nodes.append({"id": cid, "type": "Character", "text": text})

    # Trait nodes and edges
    for k, v in traits.items():
        nid = f"trait:{k}"
        nodes.append({"id": nid, "type": "Trait", "name": k, "score": float(v)})
        edges.append({"from": cid, "to": nid, "type": "HAS_TRAIT", "weight": float(v)})

    # Emotion nodes and edges (HF pipeline returns list of {label, score})
    for e in emotions:
        label = e.get("label")
        score = float(e.get("score", 0.0))
        nid = f"emotion:{label}"
        nodes.append({"id": nid, "type": "Emotion", "name": label, "score": score})
        edges.append({"from": cid, "to": nid, "type": "HAS_EMOTION", "weight": score})

    return {"nodes": nodes, "edges": edges}


def format_payload_json(text: str, character_id: str | None = None) -> str:
    """Return a JSON string of the payload (encoded with compact separators)."""
    import json

    payload = create_langraph_payload(text, character_id=character_id)
    return json.dumps(payload, separators=(",", ":"))
