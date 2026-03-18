"""Local JSON catalog provider — last-resort fallback.

Uses the curated hotels.json + FAISS semantic search.
Always marks results with fonte="local" so disclaimers are shown to users.
"""

import json
import logging
from pathlib import Path

from .base import HotelResult, HotelSearchInput

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

# Copied from tools.py to avoid circular import
_CITY_ALIASES: dict[str, str] = {
    "maceio": "maceió", "maceió": "maceió",
    "macapa": "macapá", "macapá": "macapá",
    "morro de sao paulo": "morro de são paulo", "morro de são paulo": "morro de são paulo",
    "lencois": "lençóis", "lençóis": "lençóis", "chapada diamantina": "lençóis",
    "ilheus": "ilhéus", "ilhéus": "ilhéus",
    "jericoacoara": "jericoacoara", "jeri": "jericoacoara",
    "canoa quebrada": "canoa quebrada", "canoa": "canoa quebrada",
    "brasilia": "brasília", "brasília": "brasília", "df": "brasília",
    "vitoria": "vitória", "vitória": "vitória",
    "goiania": "goiânia", "goiânia": "goiânia",
    "pirenopolis": "pirenópolis", "pirenópolis": "pirenópolis",
    "alto paraiso": "alto paraíso", "alto paraíso": "alto paraíso", "chapada dos veadeiros": "alto paraíso",
    "sao luis": "são luís", "são luis": "são luís", "são luís": "são luís",
    "barreirinhas": "barreirinhas", "lençóis maranhenses": "barreirinhas",
    "cuiaba": "cuiabá", "cuiabá": "cuiabá",
    "chapada dos guimaraes": "chapada dos guimarães", "chapada dos guimarães": "chapada dos guimarães",
    "corumba": "corumbá", "corumbá": "corumbá",
    "belo horizonte": "belo horizonte", "bh": "belo horizonte",
    "belem": "belém", "belém": "belém",
    "alter do chao": "alter do chão", "alter do chão": "alter do chão",
    "marajo": "ilha do marajó", "marajó": "ilha do marajó", "ilha do marajó": "ilha do marajó",
    "joao pessoa": "joão pessoa", "joão pessoa": "joão pessoa",
    "foz do iguacu": "foz do iguaçu", "foz do iguaçu": "foz do iguaçu", "foz": "foz do iguaçu",
    "recife": "recife", "olinda": "olinda",
    "parnaiba": "parnaíba", "parnaíba": "parnaíba", "delta do parnaíba": "parnaíba",
    "rio de janeiro": "rio de janeiro", "rio": "rio de janeiro", "rj": "rio de janeiro",
    "buzios": "búzios", "búzios": "búzios", "cabo frio": "búzios",
    "parati": "paraty", "paraty": "paraty",
    "petropolis": "petrópolis", "petrópolis": "petrópolis",
    "natal": "natal", "pipa": "pipa", "praia da pipa": "pipa",
    "porto alegre": "porto alegre", "poa": "porto alegre",
    "bento goncalves": "bento gonçalves", "bento gonçalves": "bento gonçalves", "bento": "bento gonçalves",
    "florianopolis": "florianópolis", "florianópolis": "florianópolis", "floripa": "florianópolis",
    "balneario camboriu": "balneário camboriú", "balneário camboriú": "balneário camboriú", "bc": "balneário camboriú",
    "sao paulo": "são paulo", "são paulo": "são paulo", "sp": "são paulo",
    "campos do jordao": "campos do jordão", "campos do jordão": "campos do jordão",
    "jalapao": "jalapão", "jalapão": "jalapão",
}


def _normalize(city: str) -> str:
    return _CITY_ALIASES.get(city.lower().strip(), city.lower().strip())


class LocalCatalogProvider:
    name = "local"

    def search(self, inp: HotelSearchInput) -> list[HotelResult]:
        from ..vector_store import search as rag_search

        with open(_DATA_DIR / "hotels.json", encoding="utf-8") as f:
            all_hotels = json.load(f)

        city = _normalize(inp.destination)
        city_hotels = [h for h in all_hotels if h["cidade"].lower() == city]

        if not city_hotels:
            logger.info("LocalCatalog: no hotels for '%s'", inp.destination)
            return []

        # Semantic reranking with FAISS
        query = f"{inp.destination} {' '.join(inp.preferences)}".strip()
        ranked_ids = rag_search(query, city=city, k=len(city_hotels))
        hotel_index = {h["id"]: h for h in city_hotels}

        ordered = [hotel_index[hid] for hid in ranked_ids if hid in hotel_index]
        seen = set(ranked_ids)
        ordered += [h for h in city_hotels if h["id"] not in seen]

        filtered = [h for h in ordered if h["preco_min"] <= inp.budget_per_night * 1.2]
        if not filtered:
            filtered = sorted(city_hotels, key=lambda h: h["preco_min"])[:5]

        logger.info("LocalCatalog: %d hotels for %s", len(filtered[:10]), inp.destination)
        return [
            HotelResult(
                id=h["id"],
                nome=h["nome"],
                cidade=h["cidade"],
                bairro=h["bairro"],
                preco_min=float(h["preco_min"]),
                preco_max=float(h["preco_max"]),
                amenities=h.get("amenities", []),
                nota=float(h.get("nota", 7.0)),
                tags=h.get("tags", []),
                descricao=h.get("descricao", ""),
                link_reserva=h.get("link_reserva", ""),
                telefone=h.get("telefone"),
                fonte="local",
            )
            for h in filtered[:10]
        ]
