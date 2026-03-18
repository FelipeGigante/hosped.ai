"""Liteapi hotel provider — fallback when Amadeus fails or city has no IATA.

Docs: https://docs.liteapi.travel
Free tier: available for developers/startups.
"""

import logging
import os
from datetime import datetime

import httpx

from .base import HotelResult, HotelSearchInput

logger = logging.getLogger(__name__)

_BASE = "https://api.liteapi.travel/v3.0"


def _parse_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def _nights(checkin_iso: str, checkout_iso: str) -> int:
    try:
        d1 = datetime.strptime(checkin_iso, "%Y-%m-%d")
        d2 = datetime.strptime(checkout_iso, "%Y-%m-%d")
        return max(1, (d2 - d1).days)
    except Exception:
        return 1


def _infer_tags(amenities: list[str]) -> list[str]:
    lower = " ".join(amenities).lower()
    mapping = {
        "piscina": ["pool", "piscina"],
        "praia": ["beach", "praia"],
        "café da manhã": ["breakfast", "café", "cafe"],
        "wifi": ["wifi", "internet"],
        "estacionamento": ["parking", "estacionamento"],
        "academia": ["gym", "fitness"],
        "spa": ["spa"],
    }
    return [tag for tag, kws in mapping.items() if any(k in lower for k in kws)] or ["hospedagem"]


class LiteapiProvider:
    name = "liteapi"

    def __init__(self) -> None:
        self.api_key = os.getenv("LITEAPI_KEY", "")

    def _enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, inp: HotelSearchInput) -> list[HotelResult]:
        if not self._enabled():
            raise RuntimeError("LITEAPI_KEY not configured")

        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

        # Step 1: list hotels in city
        r = httpx.get(
            f"{_BASE}/data/hotels",
            params={"countryCode": "BR", "cityName": inp.destination, "limit": 30},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        hotels_data: list[dict] = r.json().get("data", [])

        if not hotels_data:
            logger.info("Liteapi: no hotels found for %s", inp.destination)
            return []

        hotel_ids = [h["id"] for h in hotels_data[:20]]
        checkin = _parse_date(inp.checkin)
        checkout = _parse_date(inp.checkout)

        # Step 2: rates
        r = httpx.post(
            f"{_BASE}/hotels/rates",
            json={
                "hotelIds": hotel_ids,
                "checkin": checkin,
                "checkout": checkout,
                "currency": "BRL",
                "guestNationality": "BR",
                "occupancies": [{"adults": inp.guests}],
            },
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        # Response: {"data": [{"hotelId": str, "roomTypes": [...]}]}
        rates_items: list[dict] = r.json().get("data", [])

        hotel_map = {h["id"]: h for h in hotels_data}
        nights = _nights(checkin, checkout)
        results: list[HotelResult] = []

        for rate_info in rates_items:
            try:
                hotel_id = rate_info.get("hotelId", "")
                room_types = rate_info.get("roomTypes", [])
                if not room_types:
                    continue

                # Find cheapest room type by offerRetailRate
                def _price(rt: dict) -> float:
                    return float(rt.get("offerRetailRate", {}).get("amount", 9999))

                best_room = min(room_types, key=_price)
                price_total = _price(best_room)
                price_night = price_total / nights

                if price_night > inp.budget_per_night * 1.3:
                    continue

                meta = hotel_map.get(hotel_id, {})
                amenities = [a.lower() for a in meta.get("amenities", [])[:10]]
                addr = meta.get("address", {})
                bairro = addr.get("district") or addr.get("city") or inp.destination if isinstance(addr, dict) else inp.destination

                stars = meta.get("starRating", 0)
                nota = min(10.0, float(stars) * 2.0) if stars else 7.0

                results.append(HotelResult(
                    id=f"liteapi_{hotel_id}",
                    nome=meta.get("name", hotel_id).title(),
                    cidade=inp.destination.lower(),
                    bairro=bairro,
                    preco_min=round(price_night * 0.9),
                    preco_max=round(price_night * 1.1),
                    amenities=amenities,
                    nota=nota,
                    tags=_infer_tags(amenities),
                    descricao=meta.get("description", "Hotel disponível via Liteapi."),
                    link_reserva=meta.get("websiteUrl", f"https://www.booking.com/searchresults.pt-br.html?ss={inp.destination}"),
                    telefone=meta.get("phoneNumber"),
                    fonte="liteapi",
                ))
            except Exception:
                logger.debug("Skipping malformed Liteapi hotel", exc_info=True)

        logger.info("Liteapi: %d usable hotels for %s", len(results), inp.destination)
        return results
