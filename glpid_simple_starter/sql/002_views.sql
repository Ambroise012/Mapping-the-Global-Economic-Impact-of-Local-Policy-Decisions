CREATE OR REPLACE VIEW v_policy_timeline AS
SELECT p.policy_id, t.name AS territory, t.territory_type, p.title, p.policy_type, p.status,
p.announcement_date, p.adoption_date, p.effective_date, p.end_date, s.publisher,
s.title AS source_title, s.url AS source_url
FROM policy_changes p JOIN territories t ON t.territory_id=p.territory_id
JOIN sources s ON s.source_id=p.source_id;
CREATE OR REPLACE VIEW v_company_indicators AS
SELECT c.company_id, c.name AS company, c.sector, t.name AS territory, i.indicator_code,
i.period_start, i.period_end, i.value, i.unit, i.currency, i.geographic_scope,
s.publisher, s.url AS source_url
FROM company_indicators i JOIN companies c ON c.company_id=i.company_id
LEFT JOIN territories t ON t.territory_id=i.territory_id
JOIN sources s ON s.source_id=i.source_id;
CREATE OR REPLACE VIEW v_company_exposures AS
SELECT e.exposure_id, c.company_id, c.name AS company, t.territory_id, t.name AS territory,
e.exposure_type, e.exposure_score, e.exposure_basis, e.start_date, e.end_date, e.notes
FROM company_exposures e
JOIN companies c ON c.company_id=e.company_id
JOIN territories t ON t.territory_id=e.territory_id;
CREATE OR REPLACE VIEW v_company_price_returns AS
SELECT company_id, price_date, close_price,
       LAG(close_price) OVER (PARTITION BY company_id ORDER BY price_date) AS previous_close_price,
       CASE
           WHEN LAG(close_price) OVER (PARTITION BY company_id ORDER BY price_date) IS NULL THEN NULL
           ELSE (close_price - LAG(close_price) OVER (PARTITION BY company_id ORDER BY price_date)) /
                NULLIF(LAG(close_price) OVER (PARTITION BY company_id ORDER BY price_date), 0)
       END AS daily_return
FROM company_prices;
CREATE OR REPLACE VIEW v_event_study_candidates AS
SELECT p.policy_id, p.title AS policy_title, t.territory_id, t.name AS territory, p.announcement_date,
p.adoption_date, p.effective_date, c.company_id, c.name AS company,
e.exposure_id, e.exposure_type, e.exposure_score, e.exposure_basis,
e.start_date AS exposure_start_date, e.end_date AS exposure_end_date
FROM policy_changes p
JOIN territories t ON t.territory_id = p.territory_id
JOIN company_exposures e ON e.territory_id = p.territory_id
JOIN companies c ON c.company_id = e.company_id;
CREATE OR REPLACE VIEW v_territory_indicators AS
SELECT t.territory_id, t.name AS territory, t.territory_type, t.country_code,
i.indicator_code, i.period_start, i.period_end, i.value, i.unit, i.geographic_scope,
s.publisher, s.title AS source_title, s.url AS source_url, i.source_page, i.notes
FROM territory_indicators i JOIN territories t ON t.territory_id=i.territory_id
JOIN sources s ON s.source_id=i.source_id;
