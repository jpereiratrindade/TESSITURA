-- TESSITURA-TIME-001 / v0.1.4
-- Um agregado pode representar uma janela de observação, não apenas um instante.
ALTER TABLE evidence ADD COLUMN observed_start TEXT NOT NULL DEFAULT '';
ALTER TABLE evidence ADD COLUMN observed_end TEXT NOT NULL DEFAULT '';
CREATE INDEX idx_evidence_observation_interval ON evidence(observed_start, observed_end);
