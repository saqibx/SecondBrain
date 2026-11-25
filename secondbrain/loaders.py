"""Extract plain text from files. Supported: txt, md, pdf, docx, html, csv, json, code files."""

import json
import logging
import re
from html.parser import HTMLParser
from pathlib import Path

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".log",
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb",
    ".sh", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sql", ".tex",
}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | {".pdf", ".docx", ".html", ".htm", ".json"}

# Directories never worth ingesting when walking a folder.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".secondbrain", "dist", "build"}


class _HTMLTextExtractor(HTMLParser):
    _SKIP_TAGS = {"script", "style", "head", "noscript"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._parts)


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def load_file(path: Path) -> str:
    """Return the plain-text content of a file. Raises ValueError on unsupported/unreadable files."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".docx":
        return _load_docx(path)
    if suffix in (".html", ".htm"):
        return _load_html(path)
    if suffix == ".json":
        return _load_json(path)
    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[page {i + 1}]\n{text.strip()}")
    if not pages:
        raise ValueError(f"No extractable text in PDF (may be scanned images): {path.name}")
    return "\n\n".join(pages)


def _load_docx(path: Path) -> str:
    import docx

    doc = docx.Document(str(path))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def _load_html(path: Path) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.text()


def _load_json(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.dumps(json.loads(raw), indent=1, ensure_ascii=False)
    except json.JSONDecodeError:
        return raw


def discover_files(root: Path) -> list[Path]:
    """All supported files under a path (a single file, or a folder walked recursively)."""
    if root.is_file():
        return [root] if is_supported(root) else []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and is_supported(path) and not path.name.startswith("."):
            if not any(part in SKIP_DIRS or part.startswith(".") for part in path.relative_to(root).parts[:-1]):
                files.append(path)
    return files


def clean_text(text: str) -> str:
    """Normalize whitespace without destroying paragraph structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
