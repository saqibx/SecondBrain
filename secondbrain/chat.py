"""RAG pipeline: retrieve → rerank → answer with citations.

Without an LLM backend it falls back to extractive mode: the best-matching
passages are returned verbatim with their sources.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .llm import get_llm
from .store import Brain, SearchResult

SYSTEM_PROMPT = """You are SecondBrain, an assistant that answers questions using only the user's own documents.

Rules:
- Answer using ONLY the provided context passages. Do not use outside knowledge.
- Cite passages you used by their number, e.g. [1] or [2][3].
- If the context does not contain the answer, say so plainly — never guess.
- Be direct and concise."""


@dataclass
class Answer:
    text: str
    sources: list[SearchResult]
    extractive: bool = False


@dataclass
class ChatSession:
    """Holds the LLM backend and recent conversation turns for follow-up questions."""

    brain: Brain
    history: list[dict] = field(default_factory=list)
    max_history_turns: int = 4

    def __post_init__(self):
        s = self.brain.settings
        self.llm = get_llm(s.provider, s.model, s.base_url)

    @property
    def backend_description(self) -> str:
        if self.llm is None:
            return "extractive mode (no LLM — showing best-matching passages)"
        return f"{self.llm.name} ({self.llm.model})"

    def ask(self, question: str) -> Answer:
        results = self.brain.search(question)
        if not results:
            return Answer(
                text="The knowledge base is empty or nothing matched. Ingest documents first: secondbrain ingest <path>",
                sources=[],
                extractive=True,
            )

        if self.llm is None:
            return Answer(text=_format_extractive(results), sources=results, extractive=True)

        context = "\n\n".join(
            f"[{i + 1}] (from {Path(r.source).name})\n{r.text}" for i, r in enumerate(results)
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += self.history[-2 * self.max_history_turns :]
        messages.append(
            {
                "role": "user",
                "content": f"Context passages:\n\n{context}\n\nQuestion: {question}",
            }
        )

        text = self.llm.chat(messages)
        # Keep only the bare question in history so old context doesn't bloat later prompts.
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": text})
        return Answer(text=text, sources=results)


def _format_extractive(results: list[SearchResult]) -> str:
    parts = []
    for i, r in enumerate(results):
        snippet = r.text if len(r.text) <= 600 else r.text[:600] + "…"
        parts.append(f"[{i + 1}] {Path(r.source).name} (score {r.score:.2f})\n{snippet}")
    return "\n\n".join(parts)
