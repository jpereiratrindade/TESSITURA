-- TESSITURA-ARCH-002 / v0.1.1
-- A chave de idempotencia do diario pertence a uma investigacao.
DROP TRIGGER journal_no_update;
DROP TRIGGER journal_no_delete;

ALTER TABLE journal RENAME TO journal_v001;

CREATE TABLE journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE RESTRICT,
  kind TEXT NOT NULL CHECK(kind IN ('question','hypothesis','objection','decision','note')),
  content TEXT NOT NULL,
  author_label TEXT NOT NULL DEFAULT 'pesquisador-local',
  request_key TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(investigation_id,request_key)
);

INSERT INTO journal(id,investigation_id,kind,content,author_label,request_key,created_at)
SELECT id,investigation_id,kind,content,author_label,request_key,created_at FROM journal_v001;

DROP TABLE journal_v001;

CREATE TRIGGER journal_no_update BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT, 'journal is append-only'); END;
CREATE TRIGGER journal_no_delete BEFORE DELETE ON journal BEGIN SELECT RAISE(ABORT, 'journal is append-only'); END;
