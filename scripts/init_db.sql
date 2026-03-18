-- hosped.ai database initialization
-- Runs automatically on first postgres container start

-- Create dedicated databases and users
CREATE DATABASE hospedai;
CREATE DATABASE evolution;

CREATE USER hospedai WITH PASSWORD 'hospedai';
CREATE USER evolution WITH PASSWORD 'evolution';

GRANT ALL PRIVILEGES ON DATABASE hospedai TO hospedai;
GRANT ALL PRIVILEGES ON DATABASE evolution TO evolution;

-- ─────────────────────────────────────────────────────────────────────────────
-- hosped.ai schema
-- ─────────────────────────────────────────────────────────────────────────────
\c hospedai

-- ─── User Profiles — "biografia do usuário" ──────────────────────────────────
-- Persiste para sempre. Carregado no início de cada conversa.
-- Permite personalização mesmo após 6 meses de ausência.
CREATE TABLE IF NOT EXISTS user_profiles (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT UNIQUE NOT NULL,       -- phone number (JID sem @)
    phone               TEXT,
    first_name          TEXT,
    full_name           TEXT,
    email               TEXT,

    -- Preferências de viagem (atualizado a cada interação)
    preferred_budget_min    NUMERIC(10,2),
    preferred_budget_max    NUMERIC(10,2),
    preferred_trip_types    TEXT[] DEFAULT '{}',    -- ['casal', 'família', 'negócios']
    preferred_amenities     TEXT[] DEFAULT '{}',    -- ['piscina', 'café da manhã', 'pet']
    preferred_cities        TEXT[] DEFAULT '{}',    -- cidades que já buscou/visitou

    -- Comportamento
    total_searches      INT DEFAULT 0,
    total_bookings      INT DEFAULT 0,
    total_spent_brl     NUMERIC(12,2) DEFAULT 0,
    avg_budget_per_night NUMERIC(10,2),
    preferred_provider  TEXT,                       -- 'liteapi' | 'hotelbeds' | 'local'

    -- Contexto livre (LLM pode escrever observações)
    notes               TEXT,                       -- ex: "prefere hotéis boutique, alérgico a pets"

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_destination    TEXT,
    last_booking_at     TIMESTAMPTZ
);

CREATE INDEX idx_profiles_user_id ON user_profiles (user_id);
CREATE INDEX idx_profiles_last_seen ON user_profiles (last_seen_at DESC);

-- ─── Trip History — histórico completo de viagens ────────────────────────────
CREATE TABLE IF NOT EXISTS trip_history (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,

    -- Dados da busca
    destination         TEXT NOT NULL,
    checkin             TEXT,
    checkout            TEXT,
    guests              INT,
    budget_per_night    NUMERIC(10,2),
    preferences         TEXT[] DEFAULT '{}',
    trip_type           TEXT,

    -- Resultado
    hotels_shown        JSONB,                      -- top 3 apresentados
    hotel_chosen_id     TEXT,
    hotel_chosen_name   TEXT,
    inventory_source    TEXT,                       -- amadeus | liteapi | hotelbeds | local

    -- Booking (quando efetivado via API)
    booking_reference   TEXT,                       -- voucher/reference da Liteapi/Hotelbeds
    booking_status      TEXT DEFAULT 'browsing',    -- browsing | handoff | booked | cancelled
    guest_email         TEXT,                       -- email do hóspede no momento do booking
    total_paid_brl      NUMERIC(12,2),

    -- Satisfação (futuro)
    rating              INT,                        -- 1-5 estrelas pós-estadia
    feedback            TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trips_user_id ON trip_history (user_id);
CREATE INDEX idx_trips_destination ON trip_history (destination);
CREATE INDEX idx_trips_created ON trip_history (created_at DESC);
CREATE INDEX idx_trips_booking_ref ON trip_history (booking_reference) WHERE booking_reference IS NOT NULL;

-- ─── Leads — analytics de busca (registra toda shortlist apresentada) ─────────
CREATE TABLE IF NOT EXISTS leads (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    destination     TEXT NOT NULL,
    checkin         TEXT,
    checkout        TEXT,
    guests          INT,
    budget          NUMERIC(10,2),
    source          TEXT NOT NULL DEFAULT 'local',
    recommendations JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leads_user_id ON leads (user_id);
CREATE INDEX idx_leads_destination ON leads (destination);
CREATE INDEX idx_leads_created_at ON leads (created_at DESC);

-- ─── Audit log ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    event       TEXT NOT NULL,
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user_id ON audit_log (user_id);
CREATE INDEX idx_audit_event ON audit_log (event);

-- ─── Permissions ─────────────────────────────────────────────────────────────
GRANT ALL ON ALL TABLES IN SCHEMA public TO hospedai;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO hospedai;
