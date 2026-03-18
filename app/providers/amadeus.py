"""Amadeus Hotel API provider — primary inventory source.

Docs: https://developers.amadeus.com/self-service/category/hotels
Free tier: 2000 calls/month on test environment.
"""

import logging
import os
import time
from datetime import datetime

import httpx

from .base import HotelResult, HotelSearchInput

logger = logging.getLogger(__name__)

_BASE_TEST = "https://test.api.amadeus.com"
_BASE_PROD = "https://api.amadeus.com"

# Brazilian cities → IATA airport/city codes
CITY_TO_IATA: dict[str, str] = {
    # Acre
    "rio branco": "RBR",
    # Alagoas
    "maceió": "MCZ", "maceio": "MCZ",
    # Amazonas
    "manaus": "MAO",
    # Bahia
    "salvador": "SSA", "porto seguro": "BPS",
    # Ceará
    "fortaleza": "FOR",
    # Distrito Federal
    "brasília": "BSB", "brasilia": "BSB", "df": "BSB",
    # Espírito Santo
    "vitória": "VIX", "vitoria": "VIX",
    # Goiás
    "goiânia": "GYN", "goiania": "GYN",
    # Maranhão
    "são luís": "SLZ", "sao luis": "SLZ", "são luis": "SLZ",
    # Mato Grosso
    "cuiabá": "CGB", "cuiaba": "CGB",
    # Mato Grosso do Sul
    "campo grande": "CGR", "bonito": "BYO",
    # Minas Gerais
    "belo horizonte": "CNF", "bh": "CNF",
    # Pará
    "belém": "BEL", "belem": "BEL",
    # Paraíba
    "joão pessoa": "JPA", "joao pessoa": "JPA",
    # Paraná
    "curitiba": "CWB", "foz do iguaçu": "IGU", "foz do iguacu": "IGU", "foz": "IGU",
    # Pernambuco
    "recife": "REC", "fernando de noronha": "FEN", "noronha": "FEN",
    # Piauí
    "teresina": "THE",
    # Rio de Janeiro
    "rio de janeiro": "RIO", "rio": "RIO", "rj": "RIO",
    # Rio Grande do Norte
    "natal": "NAT",
    # Rio Grande do Sul
    "porto alegre": "POA", "poa": "POA", "gramado": "POA", "canela": "POA",
    # Rondônia
    "porto velho": "PVH",
    # Roraima
    "boa vista": "BVB",
    # Santa Catarina
    "florianópolis": "FLN", "florianopolis": "FLN", "floripa": "FLN",
    "balneário camboriú": "NVT", "balneario camboriu": "NVT",
    # São Paulo
    "são paulo": "SAO", "sao paulo": "SAO", "sp": "SAO",
    "campinas": "CPQ", "ubatuba": "UBT",
    # Sergipe
    "aracaju": "AJU",
    # Tocantins
    "palmas": "PMW",
}


def _parse_date(date_str: str) -> str:
    """Convert dd/mm/aaaa → YYYY-MM-DD. Returns original string if already ISO."""
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
        "piscina": ["pool", "piscina", "swimming"],
        "praia": ["beach", "praia"],
        "café da manhã": ["breakfast", "café", "cafe", "morning"],
        "wifi": ["wifi", "internet", "wireless"],
        "estacionamento": ["parking", "estacionamento"],
        "academia": ["gym", "fitness", "workout"],
        "spa": ["spa", "wellness", "massage"],
        "pet": ["pet", "dog", "animal"],
        "ar-condicionado": ["air conditioning", "air-conditioning", "ac"],
    }
    return [tag for tag, kws in mapping.items() if any(k in lower for k in kws)] or ["hospedagem"]


class AmadeusProvider:
    name = "amadeus"

    def __init__(self) -> None:
        self.client_id = os.getenv("AMADEUS_CLIENT_ID", "")
        self.client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "")
        env = os.getenv("AMADEUS_ENV", "test")
        self.base_url = _BASE_PROD if env == "production" else _BASE_TEST
        self._token: str | None = None
        self._token_expires: float = 0.0

    def _enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires - 30:
            return self._token
        resp = httpx.post(
            f"{self.base_url}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.monotonic() + data.get("expires_in", 1799)
        return self._token  # type: ignore[return-value]

    def search(self, inp: HotelSearchInput) -> list[HotelResult]:
        if not self._enabled():
            raise RuntimeError("Amadeus credentials not configured")

        iata = CITY_TO_IATA.get(inp.destination.lower().strip())
        if not iata:
            raise ValueError(f"No IATA code mapped for '{inp.destination}'")

        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Step 1: hotel IDs by city
        r = httpx.get(
            f"{self.base_url}/v1/reference-data/locations/hotels/by-city",
            params={"cityCode": iata, "radius": 20, "radiusUnit": "KM", "hotelSource": "ALL"},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        hotel_ids = [h["hotelId"] for h in r.json().get("data", [])[:30]]

        if not hotel_ids:
            logger.info("Amadeus: no hotels found for %s (%s)", inp.destination, iata)
            return []

        # Step 2: offers / prices
        checkin = _parse_date(inp.checkin)
        checkout = _parse_date(inp.checkout)
        r = httpx.get(
            f"{self.base_url}/v2/shopping/hotel-offers",
            params={
                "hotelIds": ",".join(hotel_ids[:20]),
                "adults": str(inp.guests),
                "checkInDate": checkin,
                "checkOutDate": checkout,
                "currency": "BRL",
                "bestRateOnly": "true",
            },
            headers=headers,
            timeout=20,
        )
        if r.status_code == 400:
            logger.warning("Amadeus offers 400 for %s: %s", inp.destination, r.text[:200])
            return []
        r.raise_for_status()

        nights = _nights(checkin, checkout)
        results: list[HotelResult] = []

        for item in r.json().get("data", []):
            try:
                hotel = item["hotel"]
                offers = item.get("offers", [])
                if not offers:
                    continue
                price_total = float(offers[0]["price"]["total"])
                price_night = price_total / nights

                if price_night > inp.budget_per_night * 1.3:
                    continue

                raw_amenities = hotel.get("amenities", [])
                amenities = [a.lower().replace("_", " ") for a in raw_amenities[:10]]

                # Nota: Amadeus rating is 1-5 stars → scale to 0-10
                stars = hotel.get("rating")
                nota = float(stars) * 2.0 if stars else 7.0
                nota = min(10.0, nota)

                desc = hotel.get("description", {})
                descricao = desc.get("text", "Hotel disponível.") if isinstance(desc, dict) else "Hotel disponível."

                contact = hotel.get("contact", {})
                telefone = contact.get("phone") if isinstance(contact, dict) else None

                results.append(HotelResult(
                    id=f"amadeus_{hotel['hotelId']}",
                    nome=hotel.get("name", hotel["hotelId"]).title(),
                    cidade=inp.destination.lower(),
                    bairro=hotel.get("address", {}).get("cityName", iata) if isinstance(hotel.get("address"), dict) else iata,
                    preco_min=round(price_night * 0.9),
                    preco_max=round(price_night * 1.1),
                    amenities=amenities,
                    nota=nota,
                    tags=_infer_tags(amenities),
                    descricao=descricao,
                    link_reserva=offers[0].get("self", f"https://www.booking.com/searchresults.pt-br.html?ss={inp.destination}"),
                    telefone=telefone,
                    fonte="amadeus",
                ))
            except Exception:
                logger.debug("Skipping malformed Amadeus hotel", exc_info=True)

        logger.info("Amadeus: %d usable hotels for %s", len(results), inp.destination)
        return results
