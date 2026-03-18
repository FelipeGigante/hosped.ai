"""Hotel booking via Liteapi.

Flow:
  1. prebook(offerId)          → prebookId (confirms availability, locks price ~10min)
  2. book(prebookId, guest)    → bookingId + voucher PDF link
                                 Liteapi sends confirmation email automatically.
  3. We send WhatsApp with booking reference + PDF link.

Docs: https://docs.liteapi.travel/reference/book-a-hotel-room
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.liteapi.travel/v3.0"


class LiteapiBookingError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Liteapi booking error {code}: {message}")


def prebook(offer_id: str) -> dict:
    """Step 1: Lock availability. Returns prebookId (valid ~10 min)."""
    api_key = os.getenv("LITEAPI_KEY", "")
    if not api_key:
        raise RuntimeError("LITEAPI_KEY not configured")

    r = httpx.post(
        f"{_BASE}/rates/prebook",
        json={"offerId": offer_id, "usePaymentSdk": False},
        headers={"X-API-Key": api_key},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()

    if "error" in data:
        raise LiteapiBookingError(data["error"]["code"], data["error"]["description"])

    return data.get("data", {})


def book(prebook_id: str, guest_first_name: str, guest_last_name: str, guest_email: str) -> dict:
    """Step 2: Confirm booking. Returns bookingId + voucher.

    Liteapi automatically sends confirmation email with PDF voucher to guest_email.
    """
    api_key = os.getenv("LITEAPI_KEY", "")
    if not api_key:
        raise RuntimeError("LITEAPI_KEY not configured")

    r = httpx.post(
        f"{_BASE}/rates/book",
        json={
            "prebookId": prebook_id,
            "guestInfo": {
                "guestFirstName": guest_first_name,
                "guestLastName": guest_last_name,
                "guestEmail": guest_email,
            },
        },
        headers={"X-API-Key": api_key},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    if "error" in data:
        raise LiteapiBookingError(data["error"]["code"], data["error"]["description"])

    return data.get("data", {})


def get_booking(booking_id: str) -> dict:
    """Retrieve booking details by ID (useful for status check)."""
    api_key = os.getenv("LITEAPI_KEY", "")
    r = httpx.get(
        f"{_BASE}/bookings/{booking_id}",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", {})


def cancel_booking(booking_id: str) -> dict:
    """Cancel a booking (subject to hotel cancellation policy)."""
    api_key = os.getenv("LITEAPI_KEY", "")
    r = httpx.delete(
        f"{_BASE}/bookings/{booking_id}",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", {})
