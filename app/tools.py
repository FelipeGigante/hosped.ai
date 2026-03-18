"""LangChain tools — all agent-callable functions.

Hotel search uses the provider cascade:
  Amadeus (real-time) → Liteapi (fallback) → Local JSON (last resort)

Scraping is explicitly forbidden as a data source.
"""

import json
import os
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .providers import HotelSearchInput, search_with_cascade

DATA_DIR = Path(__file__).parent / "data"

_extraction_llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_EXTRACTION", "gpt-4o-mini"), temperature=0)

# ---------- Schemas ----------

class TripIntent(BaseModel):
    destination: Optional[str] = Field(None, description="Cidade de destino normalizada (ex: salvador, rio de janeiro)")
    checkin_date: Optional[str] = Field(None, description="Data de check-in (dd/mm/aaaa) ou descrição textual")
    checkout_date: Optional[str] = Field(None, description="Data de check-out (dd/mm/aaaa) ou descrição textual")
    guests: Optional[int] = Field(None, description="Número de hóspedes")
    budget_per_night: Optional[float] = Field(None, description="Orçamento máximo por noite em R$")
    preferences: list[str] = Field(default_factory=list, description="Preferências: piscina, praia, café da manhã, pet, estacionamento...")
    trip_type: Optional[str] = Field(None, description="Perfil: casal, família, amigos, negócios, lazer")


# ---------- City normalization ----------

_CITY_ALIASES: dict[str, str] = {
    # Acre
    "rio branco": "rio branco",
    # Alagoas
    "maceió": "maceió", "maceio": "maceió", "maragogi": "maragogi",
    # Amapá
    "macapá": "macapá", "macapa": "macapá",
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
    "vitória": "vitória", "vitoria": "vitória", "guarapari": "guarapari",
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
    # Mato Grosso do Sul
    "campo grande": "campo grande", "bonito": "bonito",
    "corumbá": "corumbá", "corumba": "corumbá",
    # Minas Gerais
    "belo horizonte": "belo horizonte", "bh": "belo horizonte",
    "ouro preto": "ouro preto", "tiradentes": "tiradentes", "diamantina": "diamantina",
    # Pará
    "belém": "belém", "belem": "belém",
    "alter do chão": "alter do chão", "alter do chao": "alter do chão",
    "ilha do marajó": "ilha do marajó", "marajó": "ilha do marajó", "marajo": "ilha do marajó",
    # Paraíba
    "joão pessoa": "joão pessoa", "joao pessoa": "joão pessoa",
    "campina grande": "campina grande",
    # Paraná
    "curitiba": "curitiba",
    "foz do iguaçu": "foz do iguaçu", "foz do iguacu": "foz do iguaçu", "foz": "foz do iguaçu",
    # Pernambuco
    "recife": "recife", "olinda": "olinda",
    "porto de galinhas": "porto de galinhas",
    "fernando de noronha": "fernando de noronha", "noronha": "fernando de noronha",
    # Piauí
    "teresina": "teresina", "parnaíba": "parnaíba", "parnaiba": "parnaíba",
    # Rio de Janeiro
    "rio de janeiro": "rio de janeiro", "rio": "rio de janeiro", "rj": "rio de janeiro",
    "búzios": "búzios", "buzios": "búzios", "cabo frio": "búzios",
    "paraty": "paraty", "parati": "paraty",
    "petrópolis": "petrópolis", "petropolis": "petrópolis",
    "arraial do cabo": "arraial do cabo",
    # Rio Grande do Norte
    "natal": "natal", "pipa": "pipa", "praia da pipa": "pipa",
    # Rio Grande do Sul
    "porto alegre": "porto alegre", "poa": "porto alegre",
    "gramado": "gramado", "canela": "canela",
    "bento gonçalves": "bento gonçalves", "bento goncalves": "bento gonçalves", "bento": "bento gonçalves",
    # Santa Catarina
    "florianópolis": "florianópolis", "florianopolis": "florianópolis", "floripa": "florianópolis",
    "balneário camboriú": "balneário camboriú", "balneario camboriu": "balneário camboriú", "bc": "balneário camboriú",
    "blumenau": "blumenau", "bombinhas": "bombinhas",
    # São Paulo
    "são paulo": "são paulo", "sao paulo": "são paulo", "sp": "são paulo",
    "campos do jordão": "campos do jordão", "campos do jordao": "campos do jordão",
    "ubatuba": "ubatuba", "ilhabela": "ilhabela", "brotas": "brotas",
    # Sergipe
    "aracaju": "aracaju",
    # Tocantins
    "palmas": "palmas", "jalapão": "jalapão", "jalapao": "jalapão",
}


def _normalize_city(name: str) -> str:
    return _CITY_ALIASES.get(name.lower().strip(), name.lower().strip())


# ---------- Tools ----------

@tool
def extract_trip_intent(message: str) -> str:
    """Extrai intenção de viagem estruturada de uma mensagem em linguagem natural.
    Chame sempre que o usuário descrever detalhes da viagem (nova busca ou refinamento).
    Retorna JSON com campos extraídos — campos não mencionados ficam null."""
    structured_llm = _extraction_llm.with_structured_output(TripIntent)
    try:
        intent = structured_llm.invoke(
            "Extraia as informações de viagem desta mensagem. Raciocine passo a passo:\n"
            "1. Cidade/destino? Normalize (Rio → rio de janeiro, BH → belo horizonte)\n"
            "2. Datas? Converta para dd/mm/aaaa. Se relativo (semana santa), mantenha textual.\n"
            "3. Hóspedes? (casal = 2, família de 4 = 4)\n"
            "4. Orçamento? Número máximo em R$.\n"
            "5. Preferências? (amenities, estilo, localização)\n"
            "6. Tipo de viagem? (casal, família, amigos, negócios, lazer)\n\n"
            "Se algum campo não for mencionado, retorne null — NÃO invente.\n\n"
            f"Mensagem: {message}"
        )
        return intent.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_hotels(
    destination: str,
    checkin: str,
    checkout: str,
    guests: int,
    budget_per_night: float,
    preferences: list[str] = [],
) -> str:
    """Busca hotéis usando cascade: Amadeus (real-time) → Liteapi → catálogo local.
    Retorna lista JSON de hotéis elegíveis com score de relevância.
    NUNCA usa scraping — apenas APIs oficiais e catálogo curado."""
    inp = HotelSearchInput(
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        guests=guests,
        budget_per_night=budget_per_night,
        preferences=preferences,
    )

    results, source = search_with_cascade(inp)

    if not results:
        # No hotels found — return structured error with suggestions
        from .providers.amadeus import CITY_TO_IATA
        import json as _json
        # Try to suggest nearby cities from local catalog
        with open(DATA_DIR / "hotels.json", encoding="utf-8") as f:
            all_hotels = _json.load(f)
        available = sorted({h["cidade"].title() for h in all_hotels})
        return json.dumps({
            "error": f"Sem hotéis disponíveis em '{destination}' para as datas solicitadas.",
            "sugestoes": available[:15],
            "fonte": source,
        }, ensure_ascii=False)

    output = [h.model_dump() for h in results]
    # Inject source metadata so guardrail and agent know provenance
    return json.dumps({"hotels": output, "fonte": source, "total": len(output)}, ensure_ascii=False)


@tool
def rank_hotels(
    hotels_json: str,
    preferences: list[str],
    budget_per_night: float,
    trip_type: str = "lazer",
) -> str:
    """Ranqueia hotéis com score determinístico. LLM NÃO decide o score — apenas explica.
    Retorna top 3 com score (0-1) e reason_tags humanas."""
    data = json.loads(hotels_json)

    # Handle error passthrough
    if isinstance(data, dict) and "error" in data:
        return hotels_json

    hotels = data.get("hotels", data) if isinstance(data, dict) else data
    fonte = data.get("fonte", "unknown") if isinstance(data, dict) else "unknown"

    if not hotels:
        return json.dumps({"error": "Nenhum hotel para ranquear.", "fonte": fonte})

    trip_tags_map: dict[str, list[str]] = {
        "casal": ["romântico", "casal", "romantismo", "luxo", "spa"],
        "família": ["família", "kids", "criança", "piscina", "resort"],
        "amigos": ["agito", "vida noturna", "bar", "festas"],
        "negócios": ["business", "executivo", "trabalho", "wifi", "ar-condicionado"],
        "lazer": ["lazer", "relaxamento", "turismo", "praia"],
    }
    trip_tags = trip_tags_map.get(trip_type.lower(), ["lazer"])
    pref_lower = [p.lower() for p in preferences]

    ranked = []
    for h in hotels:
        score = 0.0
        reason_tags: list[str] = []
        hotel_attrs = [a.lower() for a in h.get("amenities", [])] + [t.lower() for t in h.get("tags", [])]

        # 30% — budget fit
        mid = (h["preco_min"] + h["preco_max"]) / 2
        if mid <= budget_per_night:
            budget_score = 1.0
            reason_tags.append("dentro do orçamento")
        elif mid <= budget_per_night * 1.1:
            budget_score = 0.7
        else:
            budget_score = max(0.0, 1.0 - (mid - budget_per_night) / budget_per_night)
        score += 0.30 * budget_score

        # 25% — preference fit
        matched_prefs = [p for p in pref_lower if any(p in attr for attr in hotel_attrs)]
        pref_score = min(1.0, len(matched_prefs) / max(len(pref_lower), 1))
        score += 0.25 * pref_score
        reason_tags.extend(matched_prefs[:2])

        # 20% — rating (normalized from 0-10 to 0-1, base 6)
        rating = float(h.get("nota", 7.0))
        score += 0.20 * max(0.0, (rating - 6.0) / 4.0)
        if rating >= 9.0:
            reason_tags.append("excelente avaliação")
        elif rating >= 8.0:
            reason_tags.append("bem avaliado")

        # 15% — trip type fit
        trip_score = 1.0 if any(t in hotel_attrs for t in trip_tags) else 0.5
        score += 0.15 * trip_score

        # 10% — safety
        if any(s in hotel_attrs for s in ["seguro", "segurança", "safe"]):
            score += 0.10
            reason_tags.append("região segura")
        else:
            score += 0.05

        ranked.append({
            "hotel": h,
            "score": round(score, 3),
            "reason_tags": list(dict.fromkeys(reason_tags))[:4],
            "fonte": h.get("fonte", fonte),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return json.dumps(ranked[:3], ensure_ascii=False)


@tool
def generate_local_guide(city: str, bairro: str = "", trip_type: str = "lazer") -> str:
    """Gera mini-guia com 3-5 sugestões locais próximas à hospedagem recomendada.
    Chame após apresentar a shortlist. Fonte: base curada — nunca inventa lugares."""
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
def create_booking_handoff(hotel_id: str, fonte: str = "local") -> str:
    """Gera CTA de reserva quando o usuário confirma um hotel.
    Para fontes 'amadeus' e 'liteapi': usa link real da API.
    Para fonte 'local': usa link_reserva do catálogo ou telefone.
    NUNCA afirma que a reserva está concluída — sistema não processa pagamento."""
    with open(DATA_DIR / "hotels.json", encoding="utf-8") as f:
        hotels = json.load(f)

    hotel = next((h for h in hotels if h["id"] == hotel_id), None)

    if not hotel:
        # Hotel from API — id starts with amadeus_ or liteapi_
        # Extract real booking data from session context if available
        booking_link = f"https://www.booking.com/search.html?ss={hotel_id.replace('amadeus_', '').replace('liteapi_', '')}"
        return json.dumps({
            "hotel_id": hotel_id,
            "hotel_name": "Hotel selecionado",
            "booking_link": booking_link,
            "message": (
                f"Ótima escolha! 🎉\n\n"
                f"🔗 *Reservar agora:*\n{booking_link}\n\n"
                "_Confirme disponibilidade e preço final no momento da reserva._"
            ),
            "booking_confirmed": False,
            "fonte": fonte,
        }, ensure_ascii=False)

    booking_link = hotel.get("link_reserva", "")
    phone = hotel.get("telefone", "")

    message_parts = [
        f"Ótima escolha! 🎉\n\n",
        f"🏨 *{hotel['nome']}* — {hotel['bairro']}, {hotel['cidade'].title()}\n",
        f"💰 R$ {hotel['preco_min']}–{hotel['preco_max']}/noite\n\n",
    ]
    if booking_link:
        message_parts.append(f"🔗 *Reservar agora:*\n{booking_link}\n")
    if phone:
        message_parts.append(f"📞 *Contato:* {phone}\n")
    message_parts.append("\n_Confirme disponibilidade e preço final com o hotel._")

    return json.dumps({
        "hotel_id": hotel_id,
        "hotel_name": hotel["nome"],
        "booking_link": booking_link,
        "phone": phone,
        "message": "".join(message_parts),
        "booking_confirmed": False,
        "fonte": "local",
    }, ensure_ascii=False)


@tool
def save_lead(user_id: str, destination: str, ranked_hotels_json: str, inventory_source: str = "unknown") -> str:
    """Registra lead e recomendações para analytics. Chame uma vez após apresentar a shortlist."""
    import asyncio
    import datetime
    from .memory.profile_store import upsert_profile, save_trip

    ranked = json.loads(ranked_hotels_json) if ranked_hotels_json else []
    lead = {
        "user_id": user_id,
        "destination": destination,
        "inventory_source": inventory_source,
        "recommendations": ranked,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    leads_path = Path(__file__).parent.parent / "leads.jsonl"
    with open(leads_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(lead, ensure_ascii=False) + "\n")

    # Update persistent profile: accumulate cities searched
    try:
        asyncio.get_event_loop().run_until_complete(
            upsert_profile(user_id, {
                "preferred_cities": [destination.lower()],
                "total_searches": 1,
            })
        )
        asyncio.get_event_loop().run_until_complete(
            save_trip(user_id, {
                "destination": destination,
                "hotels_shown": ranked[:3],
                "inventory_source": inventory_source,
                "booking_status": "browsing",
            })
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Profile update failed: %s", e)

    return json.dumps({"status": "saved", "source": inventory_source})


@tool
def book_hotel(
    offer_id: str,
    hotel_name: str,
    guest_first_name: str,
    guest_last_name: str,
    guest_email: str,
    user_id: str,
    destination: str,
    checkin: str,
    checkout: str,
    total_nights: int,
    price_per_night: float,
) -> str:
    """Efetiva a reserva de hotel via Liteapi.

    Use quando o usuário confirmou o hotel E forneceu:
      - nome completo (primeiro + último nome)
      - email para receber o voucher PDF de confirmação

    A Liteapi envia automaticamente o email de confirmação com PDF para o guest_email.
    Retorna o número de reserva e link do voucher.

    IMPORTANTE: só chame após ter offer_id válido do search_hotels."""
    import asyncio
    from .providers.booking import prebook, book, LiteapiBookingError
    from .memory.profile_store import upsert_profile, save_trip

    try:
        # Step 1: Lock availability
        prebook_data = prebook(offer_id)
        prebook_id = prebook_data.get("prebookId")
        if not prebook_id:
            return json.dumps({"error": "Não foi possível pré-reservar o quarto. Tente novamente."})

        # Step 2: Confirm booking
        booking_data = book(prebook_id, guest_first_name, guest_last_name, guest_email)
        booking_id = booking_data.get("bookingId") or booking_data.get("id", "")
        voucher_url = booking_data.get("voucherDownloadUrl") or booking_data.get("downloadUrl", "")
        status = booking_data.get("status", "confirmed")

        total_brl = price_per_night * total_nights

        # Save to profile
        try:
            asyncio.get_event_loop().run_until_complete(upsert_profile(user_id, {
                "email": guest_email,
                "first_name": guest_first_name,
                "full_name": f"{guest_first_name} {guest_last_name}",
                "preferred_cities": [destination.lower()],
            }))
            asyncio.get_event_loop().run_until_complete(save_trip(user_id, {
                "destination": destination,
                "checkin": checkin,
                "checkout": checkout,
                "hotel_chosen_name": hotel_name,
                "inventory_source": "liteapi",
                "booking_reference": booking_id,
                "booking_status": "booked",
                "guest_email": guest_email,
                "total_paid_brl": total_brl,
            }))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Profile save after booking failed: %s", e)

        receipt = (
            f"✅ *Reserva confirmada!*\n\n"
            f"🏨 *{hotel_name}*\n"
            f"📅 Check-in: {checkin} · Check-out: {checkout}\n"
            f"🌙 {total_nights} noites · 💰 R$ {total_brl:,.0f} estimado\n\n"
            f"🔖 *Número da reserva:* `{booking_id}`\n"
        )
        if voucher_url:
            receipt += f"📄 *Voucher PDF:* {voucher_url}\n"
        receipt += (
            f"\n📧 Confirmação enviada para *{guest_email}*\n"
            f"_(verifique também o spam)_\n\n"
            f"_Valores finais confirmados pela plataforma. "
            f"Apresente o voucher no check-in._"
        )

        return json.dumps({
            "booking_id": booking_id,
            "status": status,
            "voucher_url": voucher_url,
            "guest_email": guest_email,
            "receipt": receipt,
            "booking_confirmed": True,
        }, ensure_ascii=False)

    except LiteapiBookingError as e:
        if e.code == 5000:
            return json.dumps({
                "error": "Pagamento não processado. Tente reservar diretamente no site do hotel.",
                "booking_confirmed": False,
            })
        return json.dumps({"error": f"Erro na reserva: {e.message}", "booking_confirmed": False})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("book_hotel failed: %s", e)
        return json.dumps({"error": "Não foi possível concluir a reserva agora. Tente pelo link direto.", "booking_confirmed": False})


ALL_TOOLS = [
    extract_trip_intent,
    search_hotels,
    rank_hotels,
    generate_local_guide,
    save_lead,
    create_booking_handoff,
    book_hotel,
]
