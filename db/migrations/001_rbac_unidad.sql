-- Migración idempotente: segmentación por unidad (RNF-001).
-- `db/schema.sql` solo corre en la primera inicialización del volumen; para
-- bases ya existentes, aplicar esta migración manualmente:
--   docker compose exec -T db psql -U $DB_USER -d $DB_NAME < db/migrations/001_rbac_unidad.sql

ALTER TABLE fuentes   ADD COLUMN IF NOT EXISTS unidad TEXT;  -- RBAC por unidad (RNF-001)
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS unidad TEXT;  -- RBAC por unidad (RNF-001)
