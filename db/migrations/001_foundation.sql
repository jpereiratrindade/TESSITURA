-- TESSITURA-ARCH-001 / v0.1.0
-- Uma declaração de fonte NÃO equivale à confirmação de um fenômeno.
CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  record_fingerprint TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK(kind IN ('meteorological_alert','instrument_measurement','documentary_report','derived_indicator','land_cover_classification','other')),
  source_name TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  statement TEXT NOT NULL,
  location_ref TEXT NOT NULL DEFAULT '',
  valid_start TEXT NOT NULL DEFAULT '',
  valid_end TEXT NOT NULL DEFAULT '',
  observed_at TEXT NOT NULL DEFAULT '',
  provenance_uri TEXT NOT NULL DEFAULT '',
  source_sha256 TEXT NOT NULL DEFAULT '',
  validation_status TEXT NOT NULL DEFAULT 'not_validated' CHECK(validation_status='not_validated'),
  inserted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_evidence_kind ON evidence(kind);
CREATE INDEX IF NOT EXISTS idx_evidence_location ON evidence(location_ref);
CREATE INDEX IF NOT EXISTS idx_evidence_time ON evidence(valid_start,valid_end);
CREATE TABLE IF NOT EXISTS investigations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  question TEXT NOT NULL,
  location_ref TEXT NOT NULL DEFAULT '',
  valid_start TEXT NOT NULL DEFAULT '',
  valid_end TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL DEFAULT 'open' CHECK(state='open'),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS evidence_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE RESTRICT,
  evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE RESTRICT,
  relation TEXT NOT NULL CHECK(relation IN ('contextualizes','supports','contradicts','questions')),
  justification TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(investigation_id,evidence_id,relation,justification)
);
CREATE TABLE IF NOT EXISTS journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE RESTRICT,
  kind TEXT NOT NULL CHECK(kind IN ('question','hypothesis','objection','decision','note')),
  content TEXT NOT NULL,
  author_label TEXT NOT NULL DEFAULT 'pesquisador-local',
  request_key TEXT UNIQUE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  subject_type TEXT NOT NULL,
  subject_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS links_no_update BEFORE UPDATE ON evidence_links BEGIN SELECT RAISE(ABORT, 'links are append-only'); END;
CREATE TRIGGER IF NOT EXISTS links_no_delete BEFORE DELETE ON evidence_links BEGIN SELECT RAISE(ABORT, 'links are append-only'); END;
CREATE TRIGGER IF NOT EXISTS journal_no_update BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT, 'journal is append-only'); END;
CREATE TRIGGER IF NOT EXISTS journal_no_delete BEFORE DELETE ON journal BEGIN SELECT RAISE(ABORT, 'journal is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
