"""Tes factory model LLM dan embeddings (tanpa panggilan API nyata)."""
import pytest

from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core import config


@pytest.fixture
def api_keys(monkeypatch):
    """Mengisi api_key dummy agar konstruksi model sukses tanpa jaringan."""
    monkeypatch.setattr(config.settings, "groq_api_key", "dummy-key")
    monkeypatch.setattr(config.settings, "google_api_key", "dummy-key")


def test_get_chat_model_mengembalikan_chatgroq(api_keys):
    from app.core.llm import get_chat_model

    model = get_chat_model()
    assert isinstance(model, ChatGroq)
    assert model.model == "llama-3.1-8b-instant"
    assert model.max_retries == 2
    assert hasattr(model, "with_structured_output")


def test_get_chat_model_gagal_tanpa_api_key(monkeypatch):
    from app.core.llm import get_chat_model

    monkeypatch.setattr(config.settings, "groq_api_key", None)
    with pytest.raises(Exception):
        get_chat_model()


def test_get_embeddings_mengembalikan_embeddings(api_keys):
    from app.core.llm import get_embeddings

    embeddings = get_embeddings()
    assert isinstance(embeddings, GoogleGenerativeAIEmbeddings)
    assert embeddings.model == "gemini-embedding-001"