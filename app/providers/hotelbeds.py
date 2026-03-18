"""Hotelbeds API provider — secondary inventory source.

One of the largest B2B hotel distributors globally, with strong Brazil coverage.
Docs: https://developer.hotelbeds.com
Access: apply at https://developer.hotelbeds.com/register (free test environment)

Auth: HMAC-SHA256 signature per request (API key + secret + timestamp)
"""

import hashlib
import hmac
import logging
import os
import time
from datetime import datetime

import httpx

from .base import HotelResult, HotelSearchInput

logger = logging.getLogger(__name__)

_BASE_TEST = "https://api.test.hotelbeds.com"
_BASE_PROD = "https://api.hotelbeds.com"


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


def _infer_tags(facilities: list[dict]) -> list[str]:
    names = " ".join(f.get("facilityName", "").lower() for f in facilities)
    mapping = {
        "piscina": ["pool", "piscina", "swimming"],
        "praia": ["beach", "praia", "sea view"],
        "café da manhã": ["breakfast", "café", "cafe"],
        "wifi": ["wifi", "internet", "wi-fi"],
        "estacionamento": ["parking", "garage"],
        "academia": ["gym", "fitness", "sport"],
        "spa": ["spa", "wellness"],
        "restaurante": ["restaurant", "dining"],
    }
    return [tag for tag, kws in mapping.items() if any(k in names for k in kws)] or ["hospedagem"]


# Hotelbeds IATA / destination codes for Brazil
# See: https://developer.hotelbeds.com/documentation/getting-started/
CITY_TO_DEST: dict[str, str] = {
    "salvador": "SSA",
    "são paulo": "SAO", "sao paulo": "SAO", "sp": "SAO",
    "rio de janeiro": "RIO", "rio": "RIO", "rj": "RIO",
    "fortaleza": "FOR",
    "recife": "REC",
    "belém": "BEL", "belem": "BEL",
    "manaus": "MAO",
    "brasília": "BSB", "brasilia": "BSB",
    "porto alegre": "POA", "poa": "POA",
    "florianópolis": "FLN", "florianopolis": "FLN", "floripa": "FLN",
    "curitiba": "CWB",
    "belo horizonte": "BHZ", "bh": "BHZ",
    "natal": "NAT",
    "maceió": "MCZ", "maceio": "MCZ",
    "joão pessoa": "JPA", "joao pessoa": "JPA",
    "foz do iguaçu": "IGU", "foz do iguacu": "IGU",
    "gramado": "POA",  # no direct code, use Porto Alegre region
    "bonito": "CGR",
    "campo grande": "CGR",
    "aracaju": "AJU",
    "são luís": "SLZ", "sao luis": "SLZ",
}


class HotelbedsProvider:
    name = "hotelbeds"

    def __init__(self) -> None:
        self.api_key = os.getenv("HOTELBEDS_API_KEY", "")
        self.api_secret = os.getenv("HOTELBEDS_API_SECRET", "")
        env = os.getenv("HOTELBEDS_ENV", "test")
        self.base_url = _BASE_PROD if env == "production" else _BASE_TEST

    def _enabled(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _headers(self) -> dict:
        """HMAC-SHA256 signature: sha256(api_key + api_secret + utc_timestamp_seconds)"""
        ts = str(int(time.time()))
        signature = hashlib.sha256(
            (self.api_key + self.api_secret + ts).encode()
        ).hexdigest()
        return {
            "Api-key": self.api_key,
            "X-Signature": signature,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
        }

    def search(self, inp: HotelSearchInput) -> list[HotelResult]:
        if not self._enabled():
            raise RuntimeError("HOTELBEDS_API_KEY / HOTELBEDS_API_SECRET not configured")

        dest_code = CITY_TO_DEST.get(inp.destination.lower().strip())
        if not dest_code:
            raise ValueError(f"No Hotelbeds destination code for '{inp.destination}'")

        checkin = _parse_date(inp.checkin)
        checkout = _parse_date(inp.checkout)

        payload = {
            "stay": {"checkIn": checkin, "checkOut": checkout},
            "occupancies": [{"rooms": 1, "adults": inp.guests, "children": 0}],
            "destination": {"code": dest_code},
            "filter": {"maxHotels": 25, "maxRate": inp.budget_per_night * 1.3},
            "reviews": [{"type": "TRIPADVISOR", "minReviewRating": 0, "minReviews": 0}],
        }

        r = httpx.post(
            f"{self.base_url}/hotel-api/1.0/hotels",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )

        if r.status_code == 204:
            logger.info("Hotelbeds: no availability for %s", inp.destination)
            return []
        r.raise_for_status()

        nights = _nights(checkin, checkout)
        results: list[HotelResult] = []

        for item in r.json().get("hotels", {}).get("hotels", []):
            try:
                rates = item.get("rates", [])
                if not rates:
                    continue
                best_rate = min(rates, key=lambda x: float(x.get("net", 9999)))
                price_total = float(best_rate["net"])
                price_night = price_total / nights

                if price_night > inp.budget_per_night * 1.3:
                    continue

                facilities = item.get("facilities", [])
                amenities = [f.get("facilityName", "").lower() for f in facilities[:10]]

                # Hotelbeds rating: categorySimpleCode = "3EST", "4EST", "5EST"
                cat = item.get("categorySimpleCode", "")
                stars = int(cat[0]) if cat and cat[0].isdigit() else 3
                nota = min(10.0, stars * 2.0)

                # Try to get review score
                reviews = item.get("reviews", [])
                if reviews:
                    review_score = float(reviews[0].get("rate", 0))
                    if review_score > 0:
                        nota = min(10.0, review_score / 10.0)

                address = item.get("address", {})
                bairro = address.get("content", inp.destination) if isinstance(address, dict) else inp.destination

                results.append(HotelResult(
                    id=f"hotelbeds_{item['code']}",
                    nome=item.get("name", {}).get("content", str(item["code"])).title() if isinstance(item.get("name"), dict) else str(item.get("name", item["code"])),
                    cidade=inp.destination.lower(),
                    bairro=bairro,
                    preco_min=round(price_night * 0.95),
                    preco_max=round(price_night * 1.05),
                    amenities=amenities,
                    nota=nota,
                    tags=_infer_tags(facilities),
                    descricao=item.get("description", {}).get("content", "Hotel disponível via Hotelbeds.") if isinstance(item.get("description"), dict) else "Hotel disponível.",
                    link_reserva=f"https://www.booking.com/searchresults.pt-br.html?ss={inp.destination}",
                    telefone=item.get("phones", [{}])[0].get("phoneNumber") if item.get("phones") else None,
                    fonte="hotelbeds",
                ))
            except Exception:
                logger.debug("Skipping malformed Hotelbeds hotel", exc_info=True)

        logger.info("Hotelbeds: %d usable hotels for %s", len(results), inp.destination)
        return results
