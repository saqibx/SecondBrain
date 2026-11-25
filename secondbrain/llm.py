"""LLM backends for answer generation.

Priority when provider is "auto":
  1. Ollama running locally (free, private)
  2. OPENAI_API_KEY set in the environment (any OpenAI-compatible server)
  3. Extractive mode — no LLM, just the best-matching passages with sources
"""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class LLMError(Exception):
    pass


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise LLMError(f"HTTP {e.code} from {url}: {body}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise LLMError(f"Cannot reach {url}: {e}") from e


class OllamaLLM:
    """Local model served by Ollama (https://ollama.com) — free, runs on your machine."""

    name = "ollama"

    def __init__(self, model: str = ""):
        self.model = model or DEFAULT_OLLAMA_MODEL

    @staticmethod
    def available() -> bool:
        try:
            with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def installed_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
                data = json.loads(resp.read().decode())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def chat(self, messages: list[dict]) -> str:
        data = _post_json(
            f"{OLLAMA_URL}/api/chat",
            {"model": self.model, "messages": messages, "stream": False, "options": {"temperature": 0}},
        )
        if "error" in data:
            raise LLMError(f"Ollama: {data['error']}")
        return data["message"]["content"].strip()


class OpenAICompatibleLLM:
    """Any OpenAI-compatible chat API (OpenAI, Groq, OpenRouter, llama.cpp server, LM Studio...)."""

    name = "openai"

    def __init__(self, model: str = "", base_url: str = ""):
        self.model = model or DEFAULT_OPENAI_MODEL
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    def chat(self, messages: list[dict]) -> str:
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        data = _post_json(
            f"{self.base_url}/chat/completions",
            {"model": self.model, "messages": messages, "temperature": 0},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        return data["choices"][0]["message"]["content"].strip()


def get_llm(provider: str = "auto", model: str = "", base_url: str = ""):
    """Resolve the configured backend. Returns None for extractive (no-LLM) mode."""
    if provider == "none":
        return None
    if provider == "openai":
        return OpenAICompatibleLLM(model, base_url)
    if provider == "ollama" or (provider == "auto" and OllamaLLM.available()):
        llm = OllamaLLM(model)
        installed = llm.installed_models()
        if not model and installed and DEFAULT_OLLAMA_MODEL not in installed:
            # No model configured — use one the user already has installed.
            llm.model = installed[0]
        if installed or provider == "ollama":
            return llm
        # auto + Ollama running but no models pulled: fall through.
    if provider == "auto" and os.environ.get("OPENAI_API_KEY"):
        return OpenAICompatibleLLM(model, base_url)
    return None
