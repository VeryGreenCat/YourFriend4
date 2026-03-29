from __future__ import annotations
from typing import List
from agent.storage import graph_db_manager
from agent.utils.config import get_config

_CHUNK_SIZE = 300
_CHUNK_OVERLAP = 50

_embed_model = None


def _model_name() -> str:
    return get_config().embedding_model

def _chunk_text(
    text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP
) -> list[str]:
    """Split *text* into overlapping word-based chunks."""
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def _get_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(_model_name())
    return _embed_model

def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Return 768-d embeddings for *texts*."""
    model = _get_model()
    return model.encode(texts).tolist()

def index_backstory(bot_id: str, backstory: str) -> None:
    """Chunk *backstory*, embed, and store as BackstoryChunk nodes in Neo4j."""
    db = graph_db_manager.load()
    db.clear_backstory_chunks(bot_id)

    chunks = _chunk_text(backstory)
    if not chunks:
        return

    embeddings = _embed_texts(chunks)
    db.save_backstory_chunks(bot_id, chunks, embeddings)

def search_backstory(bot_id: str, query: str, top_k: int = 4) -> list[str]:
    """Return the *top_k* most relevant backstory chunk texts for *query*."""
    query_embedding = _embed_texts([query])[0]

    db = graph_db_manager.load()
    return db.search_backstory(bot_id, query_embedding, top_k)