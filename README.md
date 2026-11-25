# SecondBrain

Chat with your own documents. Point it at a file or folder — it ingests, chunks, and embeds everything locally, then lets you ask questions about it.

**Local-first and free by default.** No web server, no accounts, no cloud databases, no web search. Embeddings and reranking always run on your machine. Answers come from a local LLM via Ollama (free), an optional OpenAI-compatible API key, or a zero-setup extractive mode that just shows you the best-matching passages.

## Install

```bash
pip install .            # from a clone of this repo
```

Python 3.10+ required. The first ingest downloads two small models from Hugging Face (~220MB total, one time, then fully offline).

## Quick start

```bash
# 1. Index your documents (file or folder, recursive)
secondbrain ingest ~/Documents/notes

# 2. Chat with them
secondbrain chat
```

That's it. Re-run `ingest` any time — unchanged files are skipped, modified files are re-indexed.

## Getting real answers (instead of raw passages)

Without an LLM, SecondBrain runs in **extractive mode**: it returns the most relevant passages with sources. To get synthesized answers, pick one:

**Option A — Ollama (recommended, free, private):**
```bash
brew install ollama        # or download from https://ollama.com
ollama pull llama3.2:3b    # ~2GB; llama3.2:1b is smaller, qwen2.5:7b is better
```
SecondBrain auto-detects Ollama. Nothing else to configure.

**Option B — an OpenAI-compatible API key:**
```bash
export OPENAI_API_KEY=sk-...
secondbrain config --provider openai --model gpt-4o-mini
# Works with free-tier providers too, e.g. Groq:
#   export OPENAI_API_KEY=gsk_...
#   secondbrain config --provider openai --base-url https://api.groq.com/openai/v1 --model llama-3.1-8b-instant
```

## Commands

| Command | What it does |
|---|---|
| `secondbrain ingest <path>` | Index a file or folder (incremental) |
| `secondbrain chat` | Interactive chat with your documents |
| `secondbrain ask "question"` | One-shot question |
| `secondbrain status [--sources]` | Index size, active models, ingested files |
| `secondbrain forget <path>` | Remove a file/folder from the index |
| `secondbrain clear` | Delete the whole index (source files untouched) |
| `secondbrain config` | View or change settings |

All commands accept `--data-dir` to keep separate knowledge bases (default: `~/.secondbrain`).

## Supported file types

Text/Markdown, PDF, Word (.docx), HTML, JSON, CSV, and most source-code files. Scanned/image-only PDFs are skipped (no OCR).

## How it works

```
ingest:  file → extract text → chunk (~1000 chars, 150 overlap)
              → embed locally (BAAI/bge-small-en-v1.5) → ChromaDB on disk
ask:     question → embed → top-20 candidates → local cross-encoder rerank
              → top 6 chunks → LLM answers with citations (or extractive fallback)
```

Everything lives in `~/.secondbrain/`. Delete that folder and it's gone.

## Configuration

```bash
secondbrain config                       # show current settings
secondbrain config --provider ollama --model llama3.2:3b
secondbrain config --rerank off          # faster, slightly less accurate
secondbrain config --chunk-size 800 --top-k 8
```

API keys are read from environment variables only (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`) and never written to disk.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
