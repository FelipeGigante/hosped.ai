import json
import os
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).parent / "data"

_extraction_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ---------- Pydantic schemas ----------

class TripIntent(BaseModel):
    destination: Optional[str] = Field(None, description="Cidade de destino (ex: Salvador, Rio de Janeiro)")
    checkin_date: Optional[str] = Field(None, description="Data de check-in no formato dd/mm/aaaa ou descrição")
    checkout_date: Optional[str] = Field(None, description="Data de check-out no formato dd/mm/aaaa ou descrição")
    guests: Optional[int] = Field(None, description="Número de hóspedes")
    budget_per_night: Optional[float] = Field(None, description="Orçamento máximo por noite em reais")
    preferences: list[str] = Field(default_factory=list, description="Preferências como praia, piscina, café da manhã, segurança, estacionamento")
    trip_type: Optional[str] = Field(None, description="Perfil: casal, família, amigos, negócios, lazer")


# ---------- City normalization ----------

_CITY_ALIASES: dict[str, str] = {
    # Acre
    "rio branco": "rio branco", "xapuri": "xapuri", "cruzeiro do sul": "cruzeiro do sul",
    # Alagoas
    "maceió": "maceió", "maceio": "maceió", "maragogi": "maragogi", "penedo": "penedo",
    # Amapá
    "macapá": "macapá", "macapa": "macapá", "oiapoque": "oiapoque",
    # Amazonas
    "manaus": "manaus", "parintins": "parintins",
    # Bahia
    "salvador": "salvador", "porto seguro": "porto seguro",
    "morro de são paulo": "morro de são paulo", "morro de sao paulo": "morro de são paulo",
    "lençóis": "lençóis", "lencois": "lençóis", "chapada diamantina": "lençóis",
    "ilhéus": "ilhéus", "ilheus": "ilhéus",
    # Ceará
    "fortaleza": "fortaleza",
    "jericoacoara": "jericoacoara", "jeri": "jericoacoara",
    "canoa quebrada": "canoa quebrada", "canoa": "canoa quebrada",
    # Distrito Federal
    "brasília": "brasília", "brasilia": "brasília", "df": "brasília",
    # Espírito Santo
    "vitória": "vitória", "vitoria": "vitória", "guarapari": "guarapari", "itaúnas": "itaúnas", "itaunas": "itaúnas",
    # Goiás
    "goiânia": "goiânia", "goiania": "goiânia",
    "pirenópolis": "pirenópolis", "pirenopolis": "pirenópolis",
    "caldas novas": "caldas novas",
    "alto paraíso": "alto paraíso", "alto paraiso": "alto paraíso", "chapada dos veadeiros": "alto paraíso",
    # Maranhão
    "são luís": "são luís", "sao luis": "são luís", "são luis": "são luís",
    "barreirinhas": "barreirinhas", "lençóis maranhenses": "barreirinhas",
    # Mato Grosso
    "cuiabá": "cuiabá", "cuiaba": "cuiabá",
    "chapada dos guimarães": "chapada dos guimarães", "chapada dos guimaraes": "chapada dos guimarães",
    "alta floresta": "alta floresta",
    # Mato Grosso do Sul
    "campo grande": "campo grande",
    "bonito": "bonito",
    "corumbá": "corumbá", "corumba": "corumbá",
    # Minas Gerais
    "belo horizonte": "belo horizonte", "bh": "belo horizonte",
    "ouro preto": "ouro preto",
    "tiradentes": "tiradentes",
    "diamantina": "diamantina",
    # Pará
    "belém": "belém", "belem": "belém",
    "alter do chão": "alter do chão", "alter do chao": "alter do chão",
    "ilha do marajó": "ilha do marajó", "marajó": "ilha do marajó", "marajo": "ilha do marajó",
    # Paraíba
    "joão pessoa": "joão pessoa", "joao pessoa": "joão pessoa",
    "campina grande": "campina grande",
    # Paraná
    "curitiba": "curitiba",
    "foz do iguaçu": "foz do iguaçu", "foz do iguacu": "foz do iguaçu", "foz": "foz do iguaçu", "iguaçu": "foz do iguaçu",
    "morretes": "morretes",
    # Pernambuco
    "recife": "recife",
    "olinda": "olinda",
    "porto de galinhas": "porto de galinhas",
    "fernando de noronha": "fernando de noronha", "noronha": "fernando de noronha",
    # Piauí
    "teresina": "teresina",
    "parnaíba": "parnaíba", "parnaiba": "parnaíba",
    "delta do parnaíba": "parnaíba",
    # Rio de Janeiro
    "rio de janeiro": "rio de janeiro", "rio": "rio de janeiro", "rj": "rio de janeiro",
    "búzios": "búzios", "buzios": "búzios", "cabo frio": "búzios",
    "paraty": "paraty", "parati": "paraty",
    "petrópolis": "petrópolis", "petropolis": "petrópolis",
    "arraial do cabo": "arraial do cabo",
    # Rio Grande do Norte
    "natal": "natal",
    "pipa": "pipa", "praia da pipa": "pipa",
    "genipabu": "genipabu",
    # Rio Grande do Sul
    "porto alegre": "porto alegre", "poa": "porto alegre",
    "gramado": "gramado",
    "canela": "canela",
    "bento gonçalves": "bento gonçalves", "bento goncalves": "bento gonçalves", "bento": "bento gonçalves",
    # Rondônia
    "porto velho": "porto velho",
    # Roraima
    "boa vista": "boa vista",
    # Santa Catarina
    "florianópolis": "florianópolis", "florianopolis": "florianópolis", "floripa": "florianópolis",
    "balneário camboriú": "balneário camboriú", "balneario camboriu": "balneário camboriú", "bc": "balneário camboriú",
    "blumenau": "blumenau",
    "bombinhas": "bombinhas",
    # São Paulo
    "são paulo": "são paulo", "sao paulo": "são paulo", "sp": "são paulo",
    "campos do jordão": "campos do jordão", "campos do jordao": "campos do jordão",
    "ubatuba": "ubatuba",
    "ilhabela": "ilhabela",
    "brotas": "brotas",
    # Sergipe
    "aracaju": "aracaju",
    # Tocantins
    "palmas": "palmas",
    "jalapão": "jalapão", "jalapao": "jalapão",
}


def _normalize_city(name: str) -> str:
    return _CITY_ALIASES.get(name.lower().strip(), name.lower().strip())


# ---------- Tools ----------

@tool
def extract_trip_intent(message: str) -> str:
    """Extrai intenção de viagem estruturada de uma mensagem em linguagem natural.
    Chame sempre que o usuário descrever detalhes da viagem.
    Retorna JSON com campos extraídos — campos não mencionados ficam null."""
    structured_llm = _extraction_llm.with_structured_output(TripIntent)
    try:
        intent = structured_llm.invoke(
            "Extraia as informações de viagem desta mensagem. "
            "Se algum campo não for mencionado, deixe como null.\n\n"
            f"Mensagem: {message}"
        )
        return intent.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_hotels(
    destination: str,
    budget_per_night: float,
    guests: int,
    preferences: list[str] = [],
) -> str:
    """Busca hotéis compatíveis usando busca semântica (RAG) + filtro de orçamento.
    Retorna lista de hotéis elegíveis em JSON, ordenados por relevância semântica."""
    from .vector_store import search as rag_search

    with open(DATA_DIR / "hotels.json", encoding="utf-8") as f:
        all_hotels = json.load(f)

    city = _normalize_city(destination)
    city_hotels = [h for h in all_hotels if h["cidade"].lower() == city]

    if not city_hotels:
        available = sorted({h["cidade"].title() for h in all_hotels})
        return json.dumps({
            "error": f"Sem hotéis cadastrados em '{destination}'.",
            "sugestoes": available[:20],
        }, ensure_ascii=False)

    query = f"{destination} {' '.join(preferences)}".strip()
    hotel_index = {h["id"]: h for h in city_hotels}
    ranked_ids = rag_search(query, city=city, k=len(city_hotels))

    ordered = [hotel_index[hid] for hid in ranked_ids if hid in hotel_index]
    seen = set(ranked_ids)
    ordered += [h for h in city_hotels if h["id"] not in seen]

    filtered = [h for h in ordered if h["preco_min"] <= budget_per_night * 1.2]
    if not filtered:
        filtered = sorted(city_hotels, key=lambda h: h["preco_min"])[:5]

    return json.dumps(filtered, ensure_ascii=False)


@tool
def rank_hotels(
    hotels_json: str,
    preferences: list[str],
    budget_per_night: float,
    trip_type: str = "lazer",
) -> str:
    """Ranqueia hotéis com score determinístico. Retorna top 3 com score e justificativa."""
    hotels = json.loads(hotels_json)
    if isinstance(hotels, dict) and "error" in hotels:
        return hotels_json

    trip_tags_map: dict[str, list[str]] = {
        "casal": ["romântico", "casal", "romantismo", "luxo"],
        "família": ["família", "kids", "criança", "piscina"],
        "amigos": ["agito", "vida noturna", "bar"],
        "negócios": ["business", "executivo", "trabalho"],
        "lazer": ["lazer", "relaxamento", "turismo", "praia"],
    }
    trip_tags = trip_tags_map.get(trip_type.lower(), ["lazer"])
    pref_lower = [p.lower() for p in preferences]

    ranked = []
    for h in hotels:
        score = 0.0
        reason_tags: list[str] = []
        hotel_attrs = [a.lower() for a in h.get("amenities", [])] + [t.lower() for t in h.get("tags", [])]

        mid = (h["preco_min"] + h["preco_max"]) / 2
        if mid <= budget_per_night:
            budget_score = 1.0
            reason_tags.append("dentro do orçamento")
        elif mid <= budget_per_night * 1.1:
            budget_score = 0.7
        else:
            budget_score = max(0.0, 1.0 - (mid - budget_per_night) / budget_per_night)
        score += 0.30 * budget_score

        matched_prefs = [p for p in pref_lower if any(p in attr for attr in hotel_attrs)]
        pref_score = min(1.0, len(matched_prefs) / max(len(pref_lower), 1))
        score += 0.25 * pref_score
        reason_tags.extend(matched_prefs[:2])

        rating = h.get("nota", 7.0)
        score += 0.20 * max(0.0, (rating - 6.0) / 4.0)
        if rating >= 9.0:
            reason_tags.append("excelente avaliação")

        trip_score = 1.0 if any(t in hotel_attrs for t in trip_tags) else 0.5
        score += 0.15 * trip_score

        if "seguro" in hotel_attrs or "segurança" in hotel_attrs:
            score += 0.10
            reason_tags.append("região segura")
        else:
            score += 0.05

        ranked.append({
            "hotel": h,
            "score": round(score, 3),
            "reason_tags": list(dict.fromkeys(reason_tags))[:4],
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return json.dumps(ranked[:3], ensure_ascii=False)


@tool
def generate_local_guide(city: str, bairro: str = "", trip_type: str = "lazer") -> str:
    """Gera mini-guia local com 3 a 5 sugestões próximas à hospedagem recomendada.
    Chame após apresentar a shortlist de hotéis."""
    with open(DATA_DIR / "local_guide.json", encoding="utf-8") as f:
        places = json.load(f)

    city_lower = city.lower().strip()
    city_places = [p for p in places if p["cidade"].lower() == city_lower]

    if bairro:
        bairro_places = [p for p in city_places if bairro.lower() in p.get("bairro", "").lower()]
        if bairro_places:
            city_places = bairro_places

    CATEGORIES = ["cafe", "restaurante", "bar", "atração", "praia", "passeio"]
    seen_cats: set[str] = set()
    guide: list[dict] = []
    for place in city_places:
        cat = place.get("categoria", "")
        if cat not in seen_cats and cat in CATEGORIES:
            guide.append(place)
            seen_cats.add(cat)
        if len(guide) >= 5:
            break

    if not guide:
        guide = city_places[:5]

    return json.dumps(guide, ensure_ascii=False)


@tool
def confirm_booking(
    hotel_id: str,
    checkin: str,
    checkout: str,
    guests: int,
    total_nights: int,
    destination: str,
) -> str:
    """Gera recibo completo de confirmação quando o usuário escolhe um hotel.
    Use quando o usuário confirmar explicitamente qual hotel quer reservar.
    Retorna recibo formatado para WhatsApp com todos os dados da viagem."""
    with open(DATA_DIR / "hotels.json", encoding="utf-8") as f:
        hotels = json.load(f)

    hotel = next((h for h in hotels if h["id"] == hotel_id), None)
    if not hotel:
        return json.dumps({"error": f"Hotel '{hotel_id}' não encontrado."})

    preco_min_total = hotel["preco_min"] * total_nights
    preco_max_total = hotel["preco_max"] * total_nights

    receipt = (
        f"✅ *Reserva confirmada!*\n\n"
        f"🏨 *{hotel['nome']}*\n"
        f"📍 {hotel['bairro']}, {hotel['cidade'].title()}\n"
        f"⭐ Nota: {hotel.get('nota', '—')}/10\n\n"
        f"📅 *Check-in:* {checkin}\n"
        f"📅 *Check-out:* {checkout}\n"
        f"🌙 *Noites:* {total_nights}\n"
        f"👥 *Hóspedes:* {guests} pessoa{'s' if guests > 1 else ''}\n\n"
        f"💰 *Estimativa total:* R$ {preco_min_total:,.0f} – R$ {preco_max_total:,.0f}\n"
        f"   _(R$ {hotel['preco_min']}–{hotel['preco_max']}/noite)_\n\n"
        f"📞 *Contato:* {hotel.get('telefone', 'N/A')}\n"
        f"🔗 *Reservar agora:*\n{hotel.get('link_reserva', 'Entre em contato diretamente.')}\n\n"
        f"_Valores estimados. Confirme disponibilidade e preço final no momento da reserva._"
    )

    return json.dumps({
        "hotel_id": hotel_id,
        "hotel_name": hotel["nome"],
        "receipt": receipt,
    }, ensure_ascii=False)


@tool
def create_booking_handoff(hotel_id: str) -> str:
    """Gera CTA de reserva para o hotel escolhido pelo usuário.
    Use quando o usuário indicar interesse mas ainda não tiver confirmado todos os dados da viagem."""
    with open(DATA_DIR / "hotels.json", encoding="utf-8") as f:
        hotels = json.load(f)

    hotel = next((h for h in hotels if h["id"] == hotel_id), None)
    if not hotel:
        return json.dumps({"error": f"Hotel '{hotel_id}' não encontrado."})

    return json.dumps({
        "hotel_name": hotel["nome"],
        "booking_link": hotel.get("link_reserva", ""),
        "phone": hotel.get("telefone", ""),
        "message": (
            f"Ótima escolha! 🎉\n\n"
            f"*{hotel['nome']}* — {hotel['bairro']}, {hotel['cidade'].title()}\n"
            f"💰 R$ {hotel['preco_min']}–{hotel['preco_max']}/noite\n\n"
            f"👉 Reservar: {hotel.get('link_reserva', 'Entre em contato diretamente.')}\n\n"
            "_Confirme disponibilidade e valores no momento da reserva._"
        ),
    }, ensure_ascii=False)


@tool
def save_lead(user_id: str, destination: str, ranked_hotels_json: str) -> str:
    """Registra o lead e as recomendações entregues para analytics.
    Chame uma vez após apresentar a shortlist."""
    import datetime
    lead = {
        "user_id": user_id,
        "destination": destination,
        "recommendations": json.loads(ranked_hotels_json) if ranked_hotels_json else [],
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    leads_path = Path(__file__).parent.parent / "leads.jsonl"
    with open(leads_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(lead, ensure_ascii=False) + "\n")
    return json.dumps({"status": "saved"})


ALL_TOOLS = [
    extract_trip_intent,
    search_hotels,
    rank_hotels,
    generate_local_guide,
    save_lead,
]
