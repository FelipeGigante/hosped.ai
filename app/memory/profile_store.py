"""User profile store — persistent "biography" across all conversations.

Loads from PostgreSQL at the start of every conversation.
Injects profile context into the agent so it can personalize even after months.

Falls back gracefully when DATABASE_URL is not set (local dev without DB).
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_DB_URL = os.getenv("DATABASE_URL", "")


# ─────────────────────────────────────────────────────────────────────────────
# Connection pool (lazy init)
# ─────────────────────────────────────────────────────────────────────────────

_pool: Any = None


async def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    if not _DB_URL:
        return None
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(_DB_URL, min_size=1, max_size=5, command_timeout=10)
        logger.info("PostgreSQL profile pool connected")
        return _pool
    except Exception as e:
        logger.warning("PostgreSQL unavailable (%s) — profiles disabled", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Profile CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def load_profile(user_id: str) -> dict | None:
    """Load user profile from DB. Returns None if not found or DB unavailable."""
    pool = await _get_pool()
    if not pool:
        return None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_profiles WHERE user_id = $1", user_id
            )
            if not row:
                return None
            profile = dict(row)
            # Update last_seen
            await conn.execute(
                "UPDATE user_profiles SET last_seen_at = NOW() WHERE user_id = $1", user_id
            )
            return profile
    except Exception as e:
        logger.warning("load_profile failed for %s: %s", user_id, e)
        return None


async def upsert_profile(user_id: str, updates: dict) -> None:
    """Create or update user profile. Merges arrays (preferences, cities)."""
    pool = await _get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT * FROM user_profiles WHERE user_id = $1", user_id
            )
            if existing:
                # Merge array fields (don't overwrite, accumulate)
                for arr_field in ("preferred_trip_types", "preferred_amenities", "preferred_cities"):
                    if arr_field in updates and updates[arr_field]:
                        existing_arr = list(existing[arr_field] or [])
                        new_items = [x for x in updates[arr_field] if x not in existing_arr]
                        updates[arr_field] = (existing_arr + new_items)[:20]  # cap at 20

                set_clauses = []
                values = []
                i = 2
                for k, v in updates.items():
                    if k not in ("id", "user_id", "created_at"):
                        set_clauses.append(f"{k} = ${i}")
                        values.append(v)
                        i += 1
                if set_clauses:
                    await conn.execute(
                        f"UPDATE user_profiles SET {', '.join(set_clauses)}, last_seen_at = NOW() WHERE user_id = $1",
                        user_id, *values
                    )
            else:
                # New profile
                await conn.execute("""
                    INSERT INTO user_profiles (
                        user_id, phone, first_name, full_name, email,
                        preferred_budget_min, preferred_budget_max,
                        preferred_trip_types, preferred_amenities, preferred_cities,
                        total_searches, notes
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    user_id,
                    updates.get("phone", user_id),
                    updates.get("first_name"),
                    updates.get("full_name"),
                    updates.get("email"),
                    updates.get("preferred_budget_min"),
                    updates.get("preferred_budget_max"),
                    updates.get("preferred_trip_types", []),
                    updates.get("preferred_amenities", []),
                    updates.get("preferred_cities", []),
                    updates.get("total_searches", 1),
                    updates.get("notes"),
                )
    except Exception as e:
        logger.warning("upsert_profile failed for %s: %s", user_id, e)


async def save_trip(user_id: str, trip: dict) -> None:
    """Save a trip to history (search, handoff, or confirmed booking)."""
    pool = await _get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            # Ensure profile exists
            await conn.execute(
                "INSERT INTO user_profiles (user_id, phone) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
                user_id, user_id
            )
            await conn.execute("""
                INSERT INTO trip_history (
                    user_id, destination, checkin, checkout, guests,
                    budget_per_night, preferences, trip_type,
                    hotels_shown, hotel_chosen_id, hotel_chosen_name,
                    inventory_source, booking_reference, booking_status,
                    guest_email, total_paid_brl
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
            """,
                user_id,
                trip.get("destination"),
                trip.get("checkin"),
                trip.get("checkout"),
                trip.get("guests"),
                trip.get("budget_per_night"),
                trip.get("preferences", []),
                trip.get("trip_type"),
                json.dumps(trip.get("hotels_shown", [])),
                trip.get("hotel_chosen_id"),
                trip.get("hotel_chosen_name"),
                trip.get("inventory_source"),
                trip.get("booking_reference"),
                trip.get("booking_status", "browsing"),
                trip.get("guest_email"),
                trip.get("total_paid_brl"),
            )

            # Update profile stats
            if trip.get("booking_status") == "booked":
                await conn.execute("""
                    UPDATE user_profiles SET
                        total_bookings = total_bookings + 1,
                        total_spent_brl = total_spent_brl + COALESCE($2, 0),
                        last_booking_at = NOW(),
                        last_destination = $3
                    WHERE user_id = $1
                """, user_id, trip.get("total_paid_brl"), trip.get("destination"))
            else:
                await conn.execute("""
                    UPDATE user_profiles SET
                        total_searches = total_searches + 1,
                        last_destination = $2
                    WHERE user_id = $1
                """, user_id, trip.get("destination"))

    except Exception as e:
        logger.warning("save_trip failed for %s: %s", user_id, e)


# ─────────────────────────────────────────────────────────────────────────────
# Profile → context string (injected into agent)
# ─────────────────────────────────────────────────────────────────────────────

def format_profile_context(profile: dict | None) -> str:
    """Format profile as context block for the agent system prompt."""
    if not profile:
        return ""

    parts = ["[PERFIL DO CLIENTE]"]

    if profile.get("first_name"):
        parts.append(f"• Nome: {profile['first_name']}")

    if profile.get("total_bookings", 0) > 0:
        parts.append(f"• {profile['total_bookings']} reserva(s) anterior(es) conosco")
    elif profile.get("total_searches", 0) > 0:
        parts.append(f"• {profile['total_searches']} busca(s) anterior(es) — ainda não reservou")

    if profile.get("last_destination"):
        last_seen = profile.get("last_seen_at")
        if last_seen:
            try:
                delta = datetime.utcnow() - last_seen.replace(tzinfo=None)
                months = delta.days // 30
                tempo = f"há ~{months} mês(es)" if months > 0 else "recentemente"
            except Exception:
                tempo = "anteriormente"
        else:
            tempo = "anteriormente"
        parts.append(f"• Último destino: {profile['last_destination']} ({tempo})")

    if profile.get("preferred_cities"):
        cities = ", ".join(profile["preferred_cities"][:5])
        parts.append(f"• Cidades que já buscou: {cities}")

    if profile.get("preferred_trip_types"):
        parts.append(f"• Perfil de viagem: {', '.join(profile['preferred_trip_types'][:3])}")

    if profile.get("preferred_amenities"):
        parts.append(f"• Preferências conhecidas: {', '.join(profile['preferred_amenities'][:5])}")

    if profile.get("avg_budget_per_night"):
        parts.append(f"• Orçamento médio histórico: R$ {profile['avg_budget_per_night']:.0f}/noite")

    if profile.get("notes"):
        parts.append(f"• Observações: {profile['notes']}")

    if profile.get("email"):
        parts.append(f"• Email cadastrado: {profile['email']}")

    parts.append("[FIM DO PERFIL]")
    return "\n".join(parts)
