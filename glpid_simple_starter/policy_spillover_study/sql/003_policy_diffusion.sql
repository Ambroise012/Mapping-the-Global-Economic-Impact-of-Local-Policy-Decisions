BEGIN;

CREATE TABLE IF NOT EXISTS policy_diffusion_cases (
    case_id TEXT PRIMARY KEY,
    policy_family TEXT NOT NULL,
    title TEXT NOT NULL,
    origin_territory_id TEXT NOT NULL REFERENCES territories(territory_id),
    anchor_policy_title TEXT NOT NULL,
    anchor_date DATE NOT NULL,
    anchor_event_type TEXT NOT NULL CHECK (
        anchor_event_type IN ('introduced', 'adopted', 'vetoed')
    ),
    target_level TEXT NOT NULL CHECK (
        target_level IN ('state', 'federal', 'international')
    ),
    gdelt_query TEXT NOT NULL,
    scope_note TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_diffusion_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES policy_diffusion_cases(case_id) ON DELETE CASCADE,
    territory_id TEXT NOT NULL REFERENCES territories(territory_id),
    event_level TEXT NOT NULL CHECK (
        event_level IN ('city', 'state', 'federal', 'national', 'international')
    ),
    event_type TEXT NOT NULL CHECK (
        event_type IN ('introduced', 'proposed', 'adopted', 'effective', 'vetoed', 'withdrawn')
    ),
    relationship TEXT NOT NULL CHECK (
        relationship IN ('same_family', 'partial_analogue', 'successor')
    ),
    event_date DATE NOT NULL,
    policy_title TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_page TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_diffusion_attention (
    policy_family TEXT NOT NULL,
    month_start DATE NOT NULL,
    article_count BIGINT NOT NULL CHECK (article_count >= 0),
    query_text TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_page TEXT NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (policy_family, month_start),
    CHECK (EXTRACT(DAY FROM month_start) = 1)
);

CREATE TABLE IF NOT EXISTS policy_diffusion_source_checks (
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    http_status INTEGER,
    final_url TEXT NOT NULL,
    content_type TEXT,
    page_title TEXT,
    meta_description TEXT,
    content_sha256 CHAR(64),
    error_text TEXT,
    PRIMARY KEY (source_id, checked_at)
);

CREATE INDEX IF NOT EXISTS idx_policy_diffusion_events_case_date
    ON policy_diffusion_events(case_id, event_date);
CREATE INDEX IF NOT EXISTS idx_policy_diffusion_events_territory
    ON policy_diffusion_events(territory_id, event_level, event_date);
CREATE INDEX IF NOT EXISTS idx_policy_diffusion_attention_month
    ON policy_diffusion_attention(month_start, policy_family);
CREATE INDEX IF NOT EXISTS idx_policy_diffusion_source_checks_latest
    ON policy_diffusion_source_checks(source_id, checked_at DESC);

COMMIT;
