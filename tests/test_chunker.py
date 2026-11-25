import pytest

from secondbrain.chunker import chunk_text


def test_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_single_chunk():
    assert chunk_text("hello world", chunk_size=100, chunk_overlap=20) == ["hello world"]


def test_chunks_respect_size():
    text = "para one.\n\n" * 50
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 200 + 50 for c in chunks)


def test_no_content_lost():
    words = [f"word{i}" for i in range(300)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=250, chunk_overlap=40)
    joined = " ".join(chunks)
    for w in words:
        assert w in joined


def test_overlap_carries_context():
    text = ("sentence about apples. " * 20) + ("sentence about oranges. " * 20)
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=100)
    for prev, nxt in zip(chunks, chunks[1:]):
        # The start of each chunk should repeat material from the previous one.
        assert nxt[:20].strip().split(" ")[0] in prev


def test_splits_on_paragraphs_first():
    text = "first paragraph here\n\nsecond paragraph here"
    chunks = chunk_text(text, chunk_size=25, chunk_overlap=5)
    assert any("first" in c for c in chunks)
    assert any("second" in c for c in chunks)


def test_giant_unbroken_string():
    text = "x" * 5000
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)
    assert all(len(c) <= 1100 for c in chunks)
    assert sum(len(c) for c in chunks) >= 5000


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=100, chunk_overlap=100)
