BEGIN;

ALTER TABLE policy_diffusion_events
    DROP CONSTRAINT IF EXISTS policy_diffusion_events_event_level_check;

ALTER TABLE policy_diffusion_events
    ADD CONSTRAINT policy_diffusion_events_event_level_check
    CHECK (event_level IN ('city', 'state', 'federal', 'national', 'international'));

COMMIT;
