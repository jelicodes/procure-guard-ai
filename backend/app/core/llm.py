"""Factory model LLM dan embeddings."""
from __future__ import annotations

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq

from app.core.config import settings


def get_chat_model() -> ChatGroq:
    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.0,
        max_retries=2,
        api_key=settings.groq_api_key,
    )


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        api_key=settings.google_api_key,
    )