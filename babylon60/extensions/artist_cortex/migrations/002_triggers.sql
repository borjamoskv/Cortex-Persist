-- =========================
-- TRIGGERS
-- =========================

CREATE TRIGGER IF NOT EXISTS trg_cortex_artifacts_touch
AFTER UPDATE ON cortex_artifacts
FOR EACH ROW
BEGIN
  UPDATE cortex_artifacts
  SET updated_at = datetime('now')
  WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_cortex_artifacts_purity_fail
AFTER INSERT ON cortex_artifacts
FOR EACH ROW
WHEN NEW.originality_raw < 0.20
  AND NEW.status = 'draft'
BEGIN
  INSERT INTO cortex_metrics (
    artifact_id, metric_name, metric_value, metric_target, metric_threshold, verdict, rationale
  ) VALUES (
    NEW.id,
    'originality',
    NEW.originality_raw,
    0.60,
    0.20,
    'fail',
    'Baja originalidad cruda. Riesgo de pudrición estética por inercia recombinatoria.'
  );
END;

CREATE TRIGGER IF NOT EXISTS trg_cortex_artifacts_friction_warn
AFTER INSERT ON cortex_artifacts
FOR EACH ROW
WHEN NEW.friction_ms > 180000
BEGIN
  INSERT INTO cortex_metrics (
    artifact_id, metric_name, metric_value, metric_target, metric_threshold, verdict, rationale
  ) VALUES (
    NEW.id,
    'friction',
    CAST(NEW.friction_ms AS REAL),
    60000,
    180000,
    'warn',
    'La fricción entre idea y ejecución supera el umbral operativo.'
  );
END;

CREATE TRIGGER IF NOT EXISTS trg_cortex_attention_penalty
AFTER INSERT ON cortex_artifacts
FOR EACH ROW
WHEN NEW.attention_yield < 0.35
BEGIN
  INSERT INTO cortex_metrics (
    artifact_id, metric_name, metric_value, metric_target, metric_threshold, verdict, rationale
  ) VALUES (
    NEW.id,
    'attention',
    NEW.attention_yield,
    0.65,
    0.35,
    'warn',
    'La pieza existe, pero su supervivencia distributiva está en zona de anemia.'
  );
END;

CREATE TRIGGER IF NOT EXISTS trg_cortex_reject_on_missing_hash
AFTER INSERT ON cortex_artifacts
FOR EACH ROW
WHEN NEW.aesthetic_hash IS NULL OR length(trim(NEW.aesthetic_hash)) = 0
BEGIN
  UPDATE cortex_artifacts
  SET status = 'rejected'
  WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_cortex_lock_anchor_guard
BEFORE UPDATE ON cortex_anchors
FOR EACH ROW
WHEN OLD.locked = 1 AND OLD.anchor_value <> NEW.anchor_value
BEGIN
  SELECT RAISE(ABORT, 'Anchor locked: mutation denied.');
END;
