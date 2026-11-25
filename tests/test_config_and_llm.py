from secondbrain.config import Settings
from secondbrain.llm import OpenAICompatibleLLM, get_llm


def test_settings_roundtrip(tmp_path):
    s = Settings(provider="ollama", model="llama3.2:3b", rerank=False)
    s.save(tmp_path)
    loaded = Settings.load(tmp_path)
    assert loaded.provider == "ollama"
    assert loaded.model == "llama3.2:3b"
    assert loaded.rerank is False


def test_settings_defaults_on_missing_file(tmp_path):
    s = Settings.load(tmp_path)
    assert s.provider == "auto"
    assert s.rerank is True


def test_settings_ignores_unknown_keys(tmp_path):
    (tmp_path / "config.json").write_text('{"provider": "none", "old_removed_field": 1}')
    assert Settings.load(tmp_path).provider == "none"


def test_provider_none_returns_no_llm():
    assert get_llm("none") is None


def test_provider_openai_reads_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    llm = get_llm("openai", model="llama-3.1-8b-instant")
    assert isinstance(llm, OpenAICompatibleLLM)
    assert llm.base_url == "https://api.groq.com/openai/v1"
    assert llm.model == "llama-3.1-8b-instant"


def test_auto_without_anything_is_extractive(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("secondbrain.llm.OllamaLLM.available", staticmethod(lambda: False))
    assert get_llm("auto") is None
