"""Vector store: local sentence-transformers embeddings persisted in ChromaDB.

Ingestion is incremental — a manifest of content hashes means unchanged files
are skipped and modified files have their old chunks replaced.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .config import BGE_QUERY_PREFIX, DEFAULT_DATA_DIR, Settings
from .chunker import chunk_text
from .loaders import clean_text, discover_files, load_file

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    text: str
    source: str
    score: float


@dataclass
class IngestReport:
    added: list[str]
    updated: list[str]
    skipped: int
    failed: list[tuple[str, str]]  # (path, reason)
    chunks: int


class Brain:
    """Owns the vector store, the manifest, and the embedding/rerank models."""

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR, settings: Settings | None = None):
        self.data_dir = Path(data_dir)
        self.settings = settings or Settings.load(self.data_dir)
        self.manifest_path = self.data_dir / "manifest.json"
        self._embedder = None
        self._reranker = None
        self._collection = None

    # -- lazy model/DB loading (imports are slow; only pay when actually used) --

    @property
    def collection(self):
        if self._collection is None:
            import chromadb

            self.data_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.data_dir / "chroma"))
            self._collection = client.get_or_create_collection(
                name="documents", metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    @property
    def embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model %s", self.settings.embedding_model)
            self._embedder = SentenceTransformer(self.settings.embedding_model)
        return self._embedder

    @property
    def reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder

            from .config import DEFAULT_RERANK_MODEL

            self._reranker = CrossEncoder(DEFAULT_RERANK_MODEL)
        return self._reranker

    # -- manifest --

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text())
            except json.JSONDecodeError:
                logger.warning("Corrupt manifest, starting fresh")
        return {}

    def _save_manifest(self, manifest: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=1))

    # -- ingestion --

    def ingest(self, target: Path, on_progress=None) -> IngestReport:
        """Ingest a file or folder. Unchanged files (by content hash) are skipped."""
        target = Path(target).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"No such file or folder: {target}")

        files = discover_files(target)
        manifest = self._load_manifest()
        report = IngestReport(added=[], updated=[], skipped=0, failed=[], chunks=0)

        for path in files:
            key = str(path)
            try:
                content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as e:
                report.failed.append((key, str(e)))
                continue

            existing = manifest.get(key)
            if existing and existing.get("hash") == content_hash:
                report.skipped += 1
                continue

            if on_progress:
                on_progress(path)
            try:
                n = self._ingest_one(path, content_hash, replace=existing is not None)
            except Exception as e:
                logger.warning("Failed to ingest %s: %s", path, e)
                report.failed.append((key, str(e)))
                continue

            manifest[key] = {"hash": content_hash, "chunks": n}
            self._save_manifest(manifest)
            report.chunks += n
            (report.updated if existing else report.added).append(key)

        return report

    def _ingest_one(self, path: Path, content_hash: str, replace: bool) -> int:
        text = clean_text(load_file(path))
        chunks = chunk_text(text, self.settings.chunk_size, self.settings.chunk_overlap)
        if not chunks:
            raise ValueError("File produced no text")

        if replace:
            self.collection.delete(where={"source": str(path)})

        doc_id = hashlib.sha256(str(path).encode()).hexdigest()[:16]
        ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
        embeddings = self.embedder.encode(chunks, show_progress_bar=False, normalize_embeddings=True)
        metadatas = [{"source": str(path), "chunk": i, "hash": content_hash} for i in range(len(chunks))]
        # Chroma caps batch sizes; 512 stays well under every backend's limit.
        for start in range(0, len(chunks), 512):
            end = start + 512
            self.collection.upsert(
                ids=ids[start:end],
                documents=chunks[start:end],
                embeddings=embeddings[start:end].tolist(),
                metadatas=metadatas[start:end],
            )
        return len(chunks)

    # -- retrieval --

    def search(self, query: str, k: int | None = None) -> list[SearchResult]:
        """Embed the query, fetch candidates, optionally rerank, return the best chunks."""
        if self.collection.count() == 0:
            return []

        retrieve_k = min(self.settings.retrieve_k, self.collection.count())
        top_k = k or self.settings.top_k

        embed_query = query
        if "bge-" in self.settings.embedding_model:
            embed_query = BGE_QUERY_PREFIX + query
        query_emb = self.embedder.encode([embed_query], normalize_embeddings=True)

        res = self.collection.query(query_embeddings=query_emb.tolist(), n_results=retrieve_k)
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        distances = res["distances"][0]

        results = [
            SearchResult(text=doc, source=meta["source"], score=1 - dist)
            for doc, meta, dist in zip(docs, metas, distances)
        ]

        if self.settings.rerank and len(results) > top_k:
            scores = self.reranker.predict([(query, r.text) for r in results], show_progress_bar=False)
            for r, s in zip(results, scores):
                r.score = float(s)
            results.sort(key=lambda r: r.score, reverse=True)

        return results[:top_k]

    # -- management --

    def forget(self, target: str) -> int:
        """Remove a previously ingested file or folder from the index. Returns files removed."""
        prefix = str(Path(target).expanduser().resolve())
        manifest = self._load_manifest()
        matches = [k for k in manifest if k == prefix or k.startswith(prefix.rstrip("/") + "/")]
        for key in matches:
            self.collection.delete(where={"source": key})
            del manifest[key]
        self._save_manifest(manifest)
        return len(matches)

    def clear(self) -> None:
        """Delete the entire index."""
        import chromadb
        import shutil

        self._collection = None
        chroma_dir = self.data_dir / "chroma"
        if chroma_dir.exists():
            client = chromadb.PersistentClient(path=str(chroma_dir))
            try:
                client.delete_collection("documents")
            except Exception:
                pass
            shutil.rmtree(chroma_dir, ignore_errors=True)
        if self.manifest_path.exists():
            self.manifest_path.unlink()

    def stats(self) -> dict:
        manifest = self._load_manifest()
        return {
            "files": len(manifest),
            "chunks": sum(v.get("chunks", 0) for v in manifest.values()),
            "sources": sorted(manifest.keys()),
            "data_dir": str(self.data_dir),
        }
