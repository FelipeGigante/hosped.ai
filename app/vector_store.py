"""FAISS vector store built from hotels.json at startup.

Each hotel is embedded as a rich text document combining name, city, neighborhood,
amenities, tags and description — enabling semantic queries like
"hotel romântico perto da praia com café da manhã".
"""

import json
import logging
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# Multilingual model — handles Portuguese well, ~120MB, runs locally
_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_store: FAISS | None = None


def _hotel_to_doc(hotel: dict) -> Document:
    text = (
        f"Hotel: {hotel['nome']}\n"
        f"Cidade: {hotel['cidade']} | Bairro: {hotel['bairro']}\n"
        f"Preço: R${hotel['preco_min']}–{hotel['preco_max']}/noite\n"
        f"Amenities: {', '.join(hotel.get('amenities', []))}\n"
        f"Tags: {', '.join(hotel.get('tags', []))}\n"
        f"Descrição: {hotel['descricao']}"
    )
    return Document(
        page_content=text,
        metadata={"hotel_id": hotel["id"], "cidade": hotel["cidade"].lower()},
    )


def build_store() -> FAISS:
    logger.info("Building FAISS hotel index (first run downloads ~120MB model)...")
    with open(DATA_DIR / "hotels.json", encoding="utf-8") as f:
        hotels = json.load(f)

    embeddings = HuggingFaceEmbeddings(model_name=_EMBED_MODEL)
    docs = [_hotel_to_doc(h) for h in hotels]
    store = FAISS.from_documents(docs, embeddings)
    logger.info("FAISS index ready — %d hotels indexed", len(docs))
    return store


def get_store() -> FAISS:
    global _store
    if _store is None:
        _store = build_store()
    return _store


def search(query: str, city: str, k: int = 10) -> list[str]:
    """Semantic search within a city. Returns list of hotel_ids ordered by relevance."""
    store = get_store()
    results = store.similarity_search(query, k=k * 3)  # over-fetch then filter
    city_lower = city.lower().strip()
    ids = [
        doc.metadata["hotel_id"]
        for doc in results
        if doc.metadata.get("cidade") == city_lower
    ]
    return ids[:k]
