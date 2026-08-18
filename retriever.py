"""
ChromaDB queries and RAG logic.

Queries the "aristotle" collection, filtered by the current topic tag,
and returns the top-k most relevant text chunks for the student's input.
"""

from __future__ import annotations

import os

import chromadb
from chromadb.utils import embedding_functions

# Path to the persisted ChromaDB store (created by loader.py)
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
_COLLECTION_NAME = "aristotle"
_EMBED_MODEL = "all-MiniLM-L6-v2"

_client: chromadb.PersistentClient | None = None
_collection = None
_embed_fn = None


def _get_collection():
    global _client, _collection, _embed_fn
    if _collection is None:
        _embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=_EMBED_MODEL
        )
        _client = chromadb.PersistentClient(path=_DB_PATH)
        _collection = _client.get_collection(
            name=_COLLECTION_NAME,
            embedding_function=_embed_fn,
        )
    return _collection


def retrieve(student_input: str, topic: str, n_results: int = 4) -> list[str]:
    """
    Query ChromaDB for the top-n chunks most relevant to student_input,
    filtered to only the chunks tagged with the given topic.

    Returns a list of raw chunk text strings.
    """
    collection = _get_collection()

    results = collection.query(
        query_texts=[student_input],
        n_results=n_results,
        where={"topic": topic},
        include=["documents"],
    )

    # results["documents"] is a list-of-lists (one inner list per query)
    documents = results.get("documents", [[]])[0]
    return documents
