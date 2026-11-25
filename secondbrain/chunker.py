"""Recursive character chunking with overlap.

Splits on the coarsest separator that keeps chunks under the size limit
(paragraphs, then lines, then sentences, then words), so chunks follow the
document's natural structure instead of cutting mid-sentence.
"""

import re

SEPARATORS = ["\n\n", "\n", ". ", " "]


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """Split text into chunks of roughly chunk_size characters with chunk_overlap between them."""
    if not text or not text.strip():
        return []
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    pieces = _split(text.strip(), chunk_size, 0)
    return _merge(pieces, chunk_size, chunk_overlap)


def _split(text: str, chunk_size: int, sep_index: int) -> list[str]:
    """Recursively break text into pieces no larger than chunk_size."""
    if len(text) <= chunk_size:
        return [text]
    if sep_index >= len(SEPARATORS):
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep = SEPARATORS[sep_index]
    # Keep the separator attached to the preceding piece so merging is lossless.
    parts = [p for p in re.split(f"({re.escape(sep)})", text) if p]
    merged_parts: list[str] = []
    for part in parts:
        if merged_parts and part == sep:
            merged_parts[-1] += part
        else:
            merged_parts.append(part)

    pieces: list[str] = []
    for part in merged_parts:
        if len(part) > chunk_size:
            pieces.extend(_split(part, chunk_size, sep_index + 1))
        else:
            pieces.append(part)
    return pieces


def _merge(pieces: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Greedily pack pieces into chunks, carrying overlap from the tail of each chunk."""
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > chunk_size:
            chunks.append(current.strip())
            current = current[-chunk_overlap:] if chunk_overlap else ""
            # Start the overlap at a word boundary.
            space = current.find(" ")
            if 0 <= space < len(current) - 1:
                current = current[space + 1 :]
        current += piece
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]
