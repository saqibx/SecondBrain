"""Configuration and on-disk layout.

Everything lives under one data directory (default ~/.secondbrain):
    chroma/         ChromaDB persistent vector store
    manifest.json   file hash index for incremental ingestion
    config.json     saved settings (never API keys — those stay in env vars)
"""

import json
import os
from dataclasses import dataclass, asdict, fields
from pathlib import Path

DEFAULT_DATA_DIR = Path(os.environ.get("SECONDBRAIN_HOME", Path.home() / ".secondbrain"))

# Free local embedding model, ~130MB one-time download from Hugging Face.
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
# BGE models retrieve best when queries carry this instruction prefix.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Free local cross-encoder used to rerank retrieved chunks, ~90MB one-time download.
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class Settings:
    # LLM backend: "auto" (ollama if running, else extractive), "ollama", "openai", "none"
    provider: str = "auto"
    model: str = ""  # backend-specific model name; sensible default chosen per backend
    base_url: str = ""  # for openai-compatible servers (Groq, OpenRouter, llama.cpp, ...)
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    rerank: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieve_k: int = 20  # candidates fetched from the vector store
    top_k: int = 6  # chunks that reach the LLM after reranking

    @classmethod
    def load(cls, data_dir: Path = DEFAULT_DATA_DIR) -> "Settings":
        path = data_dir / "config.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                known = {f.name for f in fields(cls)}
                return cls(**{k: v for k, v in data.items() if k in known})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self, data_dir: Path = DEFAULT_DATA_DIR) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "config.json").write_text(json.dumps(asdict(self), indent=2))
