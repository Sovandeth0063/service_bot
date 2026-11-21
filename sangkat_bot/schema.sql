-- SangkatConnect demo schema (SQLite). Mirrors end_to_end_system_architecture.md §5.2
-- with the refinements in mvp_scope_and_data_refined.md §4. Timestamps are UTC ISO-8601 text.

CREATE TABLE IF NOT EXISTS provinces (
    province_code TEXT PRIMARY KEY,
    province_kh   TEXT NOT NULL,
    province_en   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS districts (
    district_code TEXT PRIMARY KEY,
    province_code TEXT NOT NULL REFERENCES provinces(province_code),
    district_kh   TEXT NOT NULL,
    district_en   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS communes (
    commune_code  TEXT PRIMARY KEY,
    district_code TEXT NOT NULL REFERENCES districts(district_code),
    province_code TEXT NOT NULL REFERENCES provinces(province_code),
    commune_kh    TEXT NOT NULL,
    commune_en    TEXT NOT NULL,
    commune_type  TEXT CHECK (commune_type IN ('khum', 'sangkat'))
);

CREATE TABLE IF NOT EXISTS villages (
    village_code TEXT PRIMARY KEY,
    commune_code TEXT NOT NULL REFERENCES communes(commune_code),
    village_kh   TEXT NOT NULL,
    village_en   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commune_configs (
    commune_code        TEXT PRIMARY KEY REFERENCES communes(commune_code),
    chat_type           TEXT NOT NULL DEFAULT 'group' CHECK (chat_type IN ('group', 'channel')),
    telegram_group_id   INTEGER UNIQUE,
    hall_name_kh        TEXT NOT NULL,
    hall_phone          TEXT,
    office_days_kh      TEXT,
    office_hours_kh     TEXT,
    address_kh          TEXT,
    lat                 REAL,
    lon                 REAL,
    google_maps_url     TEXT,
    is_active           INTEGER NOT NULL DEFAULT 0,
    verification_status TEXT,
    source              TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS emergency_numbers (
    number              TEXT PRIMARY KEY,
    category            TEXT NOT NULL,
    name_kh             TEXT NOT NULL,
    name_en             TEXT NOT NULL,
    scope               TEXT NOT NULL,
    is_active           INTEGER NOT NULL,
    sort_order          INTEGER NOT NULL,
    verification_status TEXT NOT NULL,
    source              TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS local_contacts (
    id                  INTEGER PRIMARY KEY,
    commune_code        TEXT NOT NULL REFERENCES communes(commune_code),
    category            TEXT NOT NULL CHECK (
                            category IN ('fire', 'police', 'ambulance', 'hospital', 'health_center', 'village_chief')
                        ),
    name_kh             TEXT NOT NULL,
    name_en             TEXT,
    phone_numbers       TEXT,
    operating_hours_kh  TEXT,
    is_24h              INTEGER NOT NULL DEFAULT 0,
    lat                 REAL,
    lon                 REAL,
    google_maps_url     TEXT,
    distance_km         REAL,
    sort_order          INTEGER NOT NULL DEFAULT 10,
    is_active           INTEGER NOT NULL DEFAULT 1,
    verification_status TEXT NOT NULL,
    source              TEXT,
    source_ref          TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS public_services (
    id                  INTEGER PRIMARY KEY,
    commune_code        TEXT REFERENCES communes(commune_code), -- NULL = nationwide default
    service_key         TEXT NOT NULL,
    title_kh            TEXT NOT NULL,
    required_docs_kh    TEXT NOT NULL,
    fee_khr             TEXT,
    fee_conditions_kh   TEXT,
    processing_time_kh  TEXT,
    office_level        TEXT NOT NULL CHECK (
                            office_level IN ('commune_hall', 'commune_police', 'district_office', 'district_owso')
                        ),
    where_kh            TEXT,
    who_must_come_kh    TEXT,
    sort_order          INTEGER NOT NULL DEFAULT 10,
    is_active           INTEGER NOT NULL DEFAULT 1,
    verification_status TEXT NOT NULL,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS users (
    telegram_user_id INTEGER PRIMARY KEY,
    commune_code     TEXT REFERENCES communes(commune_code),
    first_seen_at    TEXT NOT NULL,
    last_active_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS announcements (
    id                     INTEGER PRIMARY KEY,
    commune_code           TEXT NOT NULL REFERENCES communes(commune_code),
    source                 TEXT NOT NULL CHECK (source IN ('seed', 'admin')),
    posted_by              INTEGER,
    text_kh                TEXT,
    photo_file_id          TEXT,
    voice_file_id          TEXT,
    group_message_id       INTEGER,
    group_voice_message_id INTEGER,
    event_date             TEXT,
    expires_at             TEXT,
    is_deleted             INTEGER NOT NULL DEFAULT 0,
    created_at             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_announcements_feed
    ON announcements (commune_code, is_deleted, created_at);

CREATE TABLE IF NOT EXISTS audit_logs (
    id            INTEGER PRIMARY KEY,
    actor_user_id INTEGER NOT NULL,
    commune_code  TEXT,
    action        TEXT NOT NULL,
    target_id     TEXT,
    metadata_json TEXT,
    created_at    TEXT NOT NULL
);
