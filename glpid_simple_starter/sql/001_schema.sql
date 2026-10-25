BEGIN;
CREATE TABLE IF NOT EXISTS territories (
 territory_id TEXT PRIMARY KEY, name TEXT NOT NULL,
 territory_type TEXT NOT NULL CHECK (territory_type IN ('district','city','metropolitan_area','region','state','country','other')),
 country_code CHAR(2), parent_territory_id TEXT REFERENCES territories(territory_id),
 description TEXT, boundary_source_url TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sources (
 source_id TEXT PRIMARY KEY, publisher TEXT NOT NULL, title TEXT NOT NULL,
 source_type TEXT NOT NULL CHECK (source_type IN ('official_law','government_statistics','company_filing','company_report','academic','news','other')),
 url TEXT NOT NULL, published_date DATE, accessed_at DATE NOT NULL DEFAULT CURRENT_DATE, notes TEXT
);
CREATE TABLE IF NOT EXISTS policy_changes (
 policy_id TEXT PRIMARY KEY, territory_id TEXT NOT NULL REFERENCES territories(territory_id),
 title TEXT NOT NULL, policy_type TEXT NOT NULL, summary TEXT,
 announcement_date DATE, adoption_date DATE, effective_date DATE, end_date DATE,
 status TEXT NOT NULL DEFAULT 'unknown' CHECK (status IN ('proposed','adopted','in_force','repealed','withdrawn','unknown')),
 affected_sector TEXT, expected_mechanism TEXT, source_id TEXT NOT NULL REFERENCES sources(source_id),
 official_reference TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (end_date IS NULL OR effective_date IS NULL OR end_date >= effective_date)
);
CREATE TABLE IF NOT EXISTS companies (
 company_id TEXT PRIMARY KEY, name TEXT NOT NULL, legal_name TEXT, country_code CHAR(2),
 sector TEXT, ticker TEXT, lei TEXT, registry_id TEXT,
 headquarters_territory_id TEXT REFERENCES territories(territory_id), website_url TEXT, notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS company_indicators (
 indicator_id TEXT PRIMARY KEY, company_id TEXT NOT NULL REFERENCES companies(company_id),
 territory_id TEXT REFERENCES territories(territory_id), indicator_code TEXT NOT NULL,
 period_start DATE NOT NULL, period_end DATE NOT NULL, value NUMERIC, unit TEXT NOT NULL,
 currency CHAR(3), geographic_scope TEXT NOT NULL CHECK (geographic_scope IN ('establishment','local','regional','national','global','unknown')),
 source_id TEXT NOT NULL REFERENCES sources(source_id), source_page TEXT, notes TEXT,
 collected_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK (period_end >= period_start)
);
CREATE TABLE IF NOT EXISTS company_exposures (
 exposure_id TEXT PRIMARY KEY,
 company_id TEXT NOT NULL REFERENCES companies(company_id),
 territory_id TEXT NOT NULL REFERENCES territories(territory_id),
 exposure_type TEXT NOT NULL CHECK (exposure_type IN ('headquarters','operations','revenue','employment','assets','tax_liability','other')),
 exposure_score NUMERIC CHECK (exposure_score >= 0 AND exposure_score <= 1),
 exposure_basis TEXT,
 source_id TEXT REFERENCES sources(source_id),
 source_page TEXT,
 start_date DATE,
 end_date DATE,
 notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
ALTER TABLE company_exposures ADD COLUMN IF NOT EXISTS source_id TEXT REFERENCES sources(source_id);
ALTER TABLE company_exposures ADD COLUMN IF NOT EXISTS source_page TEXT;
CREATE TABLE IF NOT EXISTS company_prices (
 company_price_id TEXT PRIMARY KEY,
 company_id TEXT NOT NULL REFERENCES companies(company_id),
 price_date DATE NOT NULL,
 close_price NUMERIC NOT NULL CHECK (close_price > 0),
 adjusted_close_price NUMERIC,
 volume BIGINT,
 currency CHAR(3),
 source_id TEXT REFERENCES sources(source_id),
 notes TEXT,
 collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE (company_id, price_date)
);
CREATE TABLE IF NOT EXISTS market_index_prices (
 market_index_price_id TEXT PRIMARY KEY,
 index_name TEXT NOT NULL,
 price_date DATE NOT NULL,
 close_value NUMERIC NOT NULL CHECK (close_value > 0),
 currency CHAR(3),
 source_id TEXT REFERENCES sources(source_id),
 notes TEXT,
 collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE (index_name, price_date)
);
CREATE TABLE IF NOT EXISTS territory_indicators (
 territory_indicator_id TEXT PRIMARY KEY, territory_id TEXT NOT NULL REFERENCES territories(territory_id),
 indicator_code TEXT NOT NULL, period_start DATE NOT NULL, period_end DATE NOT NULL,
 value NUMERIC, unit TEXT NOT NULL,
 geographic_scope TEXT NOT NULL CHECK (geographic_scope IN ('local','regional','national','unknown')),
 source_id TEXT NOT NULL REFERENCES sources(source_id), source_page TEXT, notes TEXT,
 collected_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK (period_end >= period_start)
);
CREATE INDEX IF NOT EXISTS idx_policy_territory_dates ON policy_changes(territory_id, effective_date);
CREATE INDEX IF NOT EXISTS idx_indicator_company_period ON company_indicators(company_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_indicator_territory ON company_indicators(territory_id);
CREATE INDEX IF NOT EXISTS idx_company_exposure_territory ON company_exposures(territory_id, company_id);
CREATE INDEX IF NOT EXISTS idx_company_prices_company_date ON company_prices(company_id, price_date);
CREATE INDEX IF NOT EXISTS idx_market_index_prices_date ON market_index_prices(index_name, price_date);
CREATE INDEX IF NOT EXISTS idx_territory_indicator_period ON territory_indicators(territory_id, indicator_code, period_start, period_end);
COMMIT;
