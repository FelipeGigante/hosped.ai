"""Hotel inventory providers — cascade fallback strategy.

Priority order (STRICT — never use scraping):

  1. Liteapi       — primary, developer-friendly, free sandbox, real inventory + booking
                     Sign up: https://liteapi.travel
  2. Hotelbeds     — largest B2B hotel distributor globally, strong Brazil coverage
                     Apply: https://developer.hotelbeds.com/register (free test env)
  3. Local JSON    — last resort; curated catalog, always adds "estimated" disclaimer

NOTE: Amadeus self-service portal is being decommissioned (July 2026).
      AmadeusProvider is kept as legacy / enterprise fallback only.
      Do NOT set AMADEUS_CLIENT_ID unless you have enterprise access.
"""

import logging

from .amadeus import AmadeusProvider
from .base import HotelResult, HotelSearchInput
from .hotelbeds import HotelbedsProvider
from .liteapi import LiteapiProvider
from .local_catalog import LocalCatalogProvider

logger = logging.getLogger(__name__)

_liteapi = LiteapiProvider()
_hotelbeds = HotelbedsProvider()
_amadeus = AmadeusProvider()   # enterprise fallback only
_local = LocalCatalogProvider()


def search_with_cascade(inp: HotelSearchInput) -> tuple[list[HotelResult], str]:
    """Search hotels using provider cascade. Returns (results, source_name).

    Falls through each provider on failure. Guarantees a response
    (empty list only when local catalog also has no hotels for the city).

    Provider order:
      1. Liteapi    — primary (LITEAPI_KEY required)
      2. Hotelbeds  — secondary (HOTELBEDS_API_KEY + HOTELBEDS_API_SECRET required)
      3. Amadeus    — enterprise legacy (AMADEUS_CLIENT_ID required; portal closing July 2026)
      4. Local JSON — guaranteed fallback, no credentials needed
    """
    # 1. Liteapi (primary)
    try:
        results = _liteapi.search(inp)
        if results:
            logger.info("Provider Liteapi → %d hotels for '%s'", len(results), inp.destination)
            return results, "liteapi"
        logger.info("Liteapi: 0 results for '%s' — trying Hotelbeds", inp.destination)
    except Exception as e:
        logger.warning("Liteapi failed for '%s': %s — trying Hotelbeds", inp.destination, e)

    # 2. Hotelbeds (secondary)
    try:
        results = _hotelbeds.search(inp)
        if results:
            logger.info("Provider Hotelbeds → %d hotels for '%s'", len(results), inp.destination)
            return results, "hotelbeds"
        logger.info("Hotelbeds: 0 results for '%s' — trying Amadeus", inp.destination)
    except Exception as e:
        logger.warning("Hotelbeds failed for '%s': %s — trying Amadeus", inp.destination, e)

    # 3. Amadeus (enterprise legacy — skipped if no credentials)
    try:
        results = _amadeus.search(inp)
        if results:
            logger.info("Provider Amadeus → %d hotels for '%s'", len(results), inp.destination)
            return results, "amadeus"
        logger.info("Amadeus: 0 results for '%s' — using local catalog", inp.destination)
    except Exception as e:
        logger.warning("Amadeus failed for '%s': %s — using local catalog", inp.destination, e)

    # 4. Local catalog (guaranteed — no credentials)
    logger.info("Provider LocalCatalog → fallback for '%s'", inp.destination)
    results = _local.search(inp)
    return results, "local"


__all__ = [
    "HotelResult",
    "HotelSearchInput",
    "LiteapiProvider",
    "HotelbedsProvider",
    "AmadeusProvider",
    "LocalCatalogProvider",
    "search_with_cascade",
]
