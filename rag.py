"""Briques communes : client Ollama, collection Chroma, embeddings."""

from __future__ import annotations

import chromadb
import ollama

import config

_ollama = ollama.Client(host=config.OLLAMA_HOST, timeout=config.LLM_TIMEOUT)


def get_chroma_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def get_collection(client: chromadb.ClientAPI | None = None, name: str | None = None):
    client = client or get_chroma_client()
    # Distance cosinus : adaptée aux embeddings de texte
    return client.get_or_create_collection(
        name=name or config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "embed_model": config.EMBED_MODEL},
    )


def embed(texts: list[str], prefix: str = "") -> list[list[float]]:
    """Calcule les embeddings via Ollama.

    `prefix` sert aux modèles qui distinguent requête et document
    (ex. nomic-embed-text : "search_query: " / "search_document: ").
    """
    inputs = [prefix + t for t in texts]
    return _ollama.embed(model=config.EMBED_MODEL, input=inputs)["embeddings"]


def _uses_nomic_prefixes() -> bool:
    return "nomic" in config.EMBED_MODEL


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embed(texts, "search_document: " if _uses_nomic_prefixes() else "")


def embed_query(text: str) -> list[float]:
    return embed([text], "search_query: " if _uses_nomic_prefixes() else "")[0]


def chat(messages: list[dict], model: str | None = None, format: dict | str | None = None) -> str:
    """Appelle le LLM. `format` peut être un schéma JSON : Ollama est alors obligé de le respecter."""
    response = _ollama.chat(
        model=model or config.LLM_MODEL,
        messages=messages,
        options={"temperature": 0.2},
        format=format,
    )
    return response["message"]["content"]
