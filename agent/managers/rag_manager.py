from __future__ import annotations

from typing import List

from langchain_text_splitters import SentenceTransformersTokenTextSplitter

from agent.storage import graph_db_manager
from agent.utils.config import get_config

_CHUNK_SIZE = 3  # number of sentences per chunk (not chars)
_CHUNK_OVERLAP = 1  # 1 sentence overlap

def _load_splitter_model() -> SentenceTransformersTokenTextSplitter:
    from pathlib import Path

    local_path = Path(get_config().spliting_model_path)
    config_file = local_path / "config.json"
    if config_file.exists():
        model_name = str(local_path)
    else:
        from sentence_transformers import SentenceTransformer

        print("Loading splitting model from Hugging Face and saving locally...")
        model_name = get_config().spliting_model
        model = SentenceTransformer(model_name)
        local_path.mkdir(parents=True, exist_ok=True)
        model.save(str(local_path))
        model_name = str(local_path)

    return SentenceTransformersTokenTextSplitter(
        chunk_overlap=_CHUNK_OVERLAP,
        model_name=model_name,
    )

def _load_embed_model():
    from sentence_transformers import SentenceTransformer
    from pathlib import Path

    _LOCAL_MODEL_PATH = Path(get_config().embedding_model_path)
    config_file = _LOCAL_MODEL_PATH / "config.json"
    if config_file.exists():
        return SentenceTransformer(str(_LOCAL_MODEL_PATH))

    print("Loading embedding model from Hugging Face and saving locally...")
    model_name = get_config().embedding_model
    model = SentenceTransformer(model_name)
    _LOCAL_MODEL_PATH.mkdir(parents=True, exist_ok=True)
    model.save(str(_LOCAL_MODEL_PATH))
    return model

_text_splitter = _load_splitter_model()
_embed_model = _load_embed_model()

def _chunk_text(
    text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP
) -> list[str]:
    global _text_splitter
    chunks = _text_splitter.split_text(text)
    print(f"Chunked backstory into {len(chunks)} chunks.", chunks)
    return chunks

def _embed_texts(texts: List[str]) -> List[List[float]]:
    global _embed_model
    return _embed_model.encode(texts).tolist()


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
