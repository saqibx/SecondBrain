import pytest

from secondbrain.cli import build_parser


def test_parser_ingest():
    args = build_parser().parse_args(["ingest", "/some/folder"])
    assert args.command == "ingest"
    assert args.path == "/some/folder"


def test_parser_ask():
    args = build_parser().parse_args(["ask", "what is x?", "--no-rerank"])
    assert args.question == "what is x?"
    assert args.no_rerank is True


def test_parser_custom_data_dir():
    args = build_parser().parse_args(["--data-dir", "/tmp/db", "status"])
    assert args.data_dir == "/tmp/db"


def test_parser_config():
    args = build_parser().parse_args(["config", "--provider", "ollama", "--rerank", "off"])
    assert args.provider == "ollama"
    assert args.rerank == "off"


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
