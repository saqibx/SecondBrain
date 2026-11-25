"""Command-line interface for SecondBrain."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_DATA_DIR, Settings


def _brain(args):
    from .store import Brain

    data_dir = Path(args.data_dir)
    settings = Settings.load(data_dir)
    if getattr(args, "no_rerank", False):
        settings.rerank = False
    return Brain(data_dir, settings)


def cmd_ingest(args):
    brain = _brain(args)
    print(f"Scanning {args.path} ...")
    report = brain.ingest(Path(args.path), on_progress=lambda p: print(f"  + {p}"))
    print(
        f"\nDone: {len(report.added)} added, {len(report.updated)} updated, "
        f"{report.skipped} unchanged, {report.chunks} new chunks."
    )
    for path, reason in report.failed:
        print(f"  ! skipped {path}: {reason}", file=sys.stderr)
    if not (report.added or report.updated or report.skipped):
        print("No supported files found at that path.", file=sys.stderr)
        sys.exit(1)


def cmd_ask(args):
    from .chat import ChatSession

    session = ChatSession(_brain(args))
    answer = session.ask(args.question)
    print(answer.text)
    if answer.sources and not answer.extractive:
        print("\nSources:")
        for i, r in enumerate(answer.sources):
            print(f"  [{i + 1}] {r.source}")


def cmd_chat(args):
    from .chat import ChatSession

    session = ChatSession(_brain(args))
    stats = session.brain.stats()
    print(f"SecondBrain v{__version__} — {stats['files']} files, {stats['chunks']} chunks indexed")
    print(f"Answering with: {session.backend_description}")
    print("Type your question, or /exit to quit, /clear to reset the conversation.\n")

    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question in ("/exit", "/quit", "exit", "quit"):
            break
        if question == "/clear":
            session.history.clear()
            print("Conversation cleared.\n")
            continue

        try:
            answer = session.ask(question)
        except Exception as e:
            print(f"error: {e}\n", file=sys.stderr)
            continue
        print(f"\nbrain> {answer.text}")
        if answer.sources and not answer.extractive:
            names = {Path(r.source).name for r in answer.sources}
            print(f"       (sources: {', '.join(sorted(names))})")
        print()


def cmd_status(args):
    from .llm import get_llm

    brain = _brain(args)
    stats = brain.stats()
    s = brain.settings
    llm = get_llm(s.provider, s.model, s.base_url)
    print(f"Data dir:   {stats['data_dir']}")
    print(f"Files:      {stats['files']}")
    print(f"Chunks:     {stats['chunks']}")
    print(f"Embeddings: {s.embedding_model} (local)")
    print(f"Reranking:  {'on' if s.rerank else 'off'} (local)")
    print(f"LLM:        {f'{llm.name} ({llm.model})' if llm else 'none — extractive mode'}")
    if args.sources and stats["sources"]:
        print("\nIngested files:")
        for src in stats["sources"]:
            print(f"  {src}")


def cmd_forget(args):
    removed = _brain(args).forget(args.path)
    print(f"Removed {removed} file(s) from the index.")


def cmd_clear(args):
    if not args.yes:
        confirm = input("This deletes the entire index (source files are untouched). Continue? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return
    _brain(args).clear()
    print("Index cleared.")


def cmd_config(args):
    data_dir = Path(args.data_dir)
    settings = Settings.load(data_dir)
    changed = False
    for key in ("provider", "model", "base_url", "chunk_size", "chunk_overlap", "top_k"):
        value = getattr(args, key, None)
        if value is not None:
            setattr(settings, key, value)
            changed = True
    if args.rerank is not None:
        settings.rerank = args.rerank == "on"
        changed = True
    if changed:
        settings.save(data_dir)
        print("Saved.")
    for k, v in vars(settings).items():
        print(f"  {k}: {v!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secondbrain",
        description="Chat with your own documents — local-first RAG. Point it at a folder, then ask questions.",
    )
    parser.add_argument("--version", action="version", version=f"secondbrain {__version__}")
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"where the index lives (default: {DEFAULT_DATA_DIR})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="index a file or folder (incremental; re-run anytime)")
    p.add_argument("path", help="file or folder to ingest")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("ask", help="ask a single question")
    p.add_argument("question")
    p.add_argument("--no-rerank", action="store_true", help="skip the reranking step (faster)")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("chat", help="interactive chat with your documents")
    p.add_argument("--no-rerank", action="store_true", help="skip the reranking step (faster)")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("status", help="show index size and active backends")
    p.add_argument("--sources", action="store_true", help="also list every ingested file")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("forget", help="remove an ingested file or folder from the index")
    p.add_argument("path")
    p.set_defaults(func=cmd_forget)

    p = sub.add_parser("clear", help="delete the whole index (never touches your source files)")
    p.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    p.set_defaults(func=cmd_clear)

    p = sub.add_parser("config", help="view or change settings")
    p.add_argument("--provider", choices=["auto", "ollama", "openai", "none"])
    p.add_argument("--model", help="model name for the chosen provider")
    p.add_argument("--base-url", dest="base_url", help="OpenAI-compatible endpoint (Groq, OpenRouter, ...)")
    p.add_argument("--rerank", choices=["on", "off"])
    p.add_argument("--chunk-size", dest="chunk_size", type=int)
    p.add_argument("--chunk-overlap", dest="chunk_overlap", type=int)
    p.add_argument("--top-k", dest="top_k", type=int)
    p.set_defaults(func=cmd_config)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
