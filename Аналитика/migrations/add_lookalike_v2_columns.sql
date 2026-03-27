-- Migration: lookalike v2 — добавить lookalike_price и lookalike_matches
ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS lookalike_price FLOAT,
  ADD COLUMN IF NOT EXISTS lookalike_matches JSONB;

CREATE INDEX IF NOT EXISTS idx_properties_lookalike_price ON properties(lookalike_price);
