-- Миграция: добавление lookalike-скоринга
-- Выполнить в Supabase SQL Editor

ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS lookalike_score FLOAT,
  ADD COLUMN IF NOT EXISTS lookalike_match_reason TEXT;

-- Индекс для фильтрации по lookalike
CREATE INDEX IF NOT EXISTS idx_properties_lookalike ON properties(lookalike_score);

COMMENT ON COLUMN properties.lookalike_score IS 'Схожесть лота с проданными объектами Estate Invest (0-100)';
COMMENT ON COLUMN properties.lookalike_match_reason IS 'Причины совпадения: тип, площадь, цена, ROI, город';
