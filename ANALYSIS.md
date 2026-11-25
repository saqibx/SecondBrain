# SecondBrain 2.0 — Refactor Analysis

Date: 2026-07-03

## What this refactor did

SecondBrain went from a multi-user Flask web service (MongoDB, Redis, auth, rate limiting, Docker, LangChain/LangGraph agents, Tavily web search, OpenAI everywhere) to a **pip-installable CLI package**: point it at a file or folder, it chunks and embeds locally, and you chat with your documents.

### Removed entirely

- **Flask app, REST API, sessions, auth, multi-user support** (`app.py`, `config.py`, `utils.py`, `logging_config.py`, `Classes/Users.py`) — it's a single-user local tool now.
- **MongoDB and Redis** — no external databases. State is files in `~/.secondbrain/`.
- **Tavily web search and the LangGraph research/email agent** (`Agents/`) — no web research, no email drafting.
- **LangChain / LangGraph / OpenAI SDK dependencies** — chunking, retrieval, and LLM calls are now plain Python (LLM calls use stdlib `urllib`, no SDK).
- **Docker, docker-compose, gunicorn, CI/CD deploy pipeline, setup.sh** — nothing to deploy; it's a package.
- **`TRAG.py` and `Helper.py`** — these files were corrupted in the repo (duplicated, interleaved merge garbage) and their logic was reimplemented cleanly.
- **Per-document AI summarization before embedding** — the old code sent every document to GPT-4o to be "summarized" before embedding. That cost money, lost detail, and hurt accuracy. Documents are now embedded as-is.
- There was **no Google Drive or Notion integration** in the code (only OpenAI + Tavily); everything external is gone regardless.

### New architecture

```
secondbrain/
  cli.py       argparse CLI: ingest / ask / chat / status / forget / clear / config
  loaders.py   text extraction: txt, md, pdf (pypdf), docx (python-docx), html, json, csv, code
  chunker.py   recursive character splitter (~1000 chars, 150 overlap, paragraph-aware)
  store.py     ChromaDB (local, persistent) + local embeddings + incremental manifest
  llm.py       backends: Ollama → OpenAI-compatible API → none (extractive)
  chat.py      RAG pipeline: retrieve 20 → rerank → top 6 → cited answer
  config.py    settings in ~/.secondbrain/config.json (never API keys)
tests/         27 tests (chunker, loaders, config, llm resolution, CLI)
pyproject.toml pip-installable, console script `secondbrain`
```

Dependencies: `chromadb`, `sentence-transformers`, `pypdf`, `python-docx`. That's it.

## Cost: $0 by default

| Component | What runs | Cost |
|---|---|---|
| Embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers, on your machine | Free (one-time ~130MB download) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2`, on your machine | Free (one-time ~90MB download) |
| Vector store | ChromaDB, persisted to `~/.secondbrain/chroma` | Free |
| Answering (default) | Ollama running a local model | Free |
| Answering (fallback) | Extractive mode — top passages shown verbatim with sources | Free, zero setup |

**No API keys are required.** The only optional key is `OPENAI_API_KEY` if you *choose* to use a hosted LLM (see below).

## Accuracy decisions

1. **`bge-small-en-v1.5` embeddings** — materially better retrieval than the common MiniLM default at nearly the same size, and better than OpenAI's `text-embedding-3-small` on many retrieval benchmarks. Queries get the BGE instruction prefix automatically.
2. **Cross-encoder reranking (on by default)** — retrieve 20 candidates, rerank with a local cross-encoder, keep the best 6. This is the single biggest free accuracy win in small RAG systems. Disable with `--no-rerank` or `secondbrain config --rerank off` if speed matters more.
3. **Structure-aware chunking with overlap** — splits on paragraphs → lines → sentences → words, 1000 chars with 150 overlap, so chunks don't cut mid-thought.
4. **Grounded prompting** — the LLM is instructed to answer only from retrieved passages, cite them `[1][2]`, and say when the answer isn't in your documents.
5. **No summarize-before-embed** — original text is embedded, so exact details (numbers, names, dates) survive retrieval.

## What you have to do

1. **Reinstall the package** (the repo now has a `.venv` you can use, or install fresh):
   ```bash
   pip install .
   ```
2. **For real (synthesized) answers, have a local model.** Ollama was already running on your machine but had no models, so during verification I pulled **`llama3.2:1b` (~1.3GB)** — it works and answered test questions correctly. For noticeably better answers, pull a bigger one when you have the disk/RAM:
   ```bash
   ollama pull llama3.2:3b     # good default, ~2GB
   ollama pull qwen2.5:7b      # better, ~4.7GB
   ```
   SecondBrain auto-detects Ollama and uses whatever model you have; pin one with `secondbrain config --provider ollama --model <name>`.
3. **Nothing else.** No `.env`, no databases, no Docker.

### Optional: hosted LLM via one API key

Only if you want better answers than a local model can give. One key maximum, read from the environment, never stored:

- **Groq (free tier)** — fast, no credit card: `export OPENAI_API_KEY=gsk_...` then
  `secondbrain config --provider openai --base-url https://api.groq.com/openai/v1 --model llama-3.1-8b-instant`
- **OpenAI (paid)** — `export OPENAI_API_KEY=sk-...` then `secondbrain config --provider openai`

Embeddings and reranking stay local either way — a key is only ever used for the final answer step, so per-question cost is tiny and your documents are only shared as the handful of retrieved passages per question.

## Old data

The old system's ChromaDB collections (OpenAI embeddings, per-user) are incompatible with the new local embeddings and weren't present in the repo anyway. Re-ingest your documents with `secondbrain ingest <path>`.

## Known limitations

- **No OCR** — scanned/image-only PDFs are reported as failed during ingest.
- English-optimized embedding model; for heavily multilingual notes switch to `BAAI/bge-m3` via `config.json` (`embedding_model`), then `secondbrain clear` and re-ingest.
- First command after install is slow (model downloads + Chroma init); everything after is fast and offline.
- Tiny local models (1B) can occasionally misread context; extractive sources are always printed so you can verify.
