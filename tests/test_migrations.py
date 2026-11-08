#!/usr/bin/env python3
"""Valida upgrade do esquema v0.1.0 e hashes historicos."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    exe, root_arg = sys.argv[1:3]
    root = Path(root_arg)
    migration_001 = root / "db/migrations/001_foundation.sql"
    content_001 = migration_001.read_bytes()
    with tempfile.TemporaryDirectory(prefix="tessitura-migration-") as tmp:
        db = Path(tmp) / "legacy.sqlite3"
        connection = sqlite3.connect(db)
        try:
            connection.execute("""CREATE TABLE schema_migrations(
                version TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))""")
            connection.executescript(content_001.decode())
            connection.execute("INSERT INTO schema_migrations(version,sha256) VALUES(?,?)",
                               ("001_foundation", hashlib.sha256(content_001).hexdigest()))
            connection.execute("INSERT INTO investigations(title,question) VALUES('A','Primeira?')")
            connection.execute("INSERT INTO investigations(title,question) VALUES('B','Segunda?')")
            connection.execute("""INSERT INTO journal(investigation_id,kind,content,request_key)
                                VALUES(1,'note','Legado','shared-key')""")
            connection.commit()
        finally:
            connection.close()

        result = subprocess.run([exe, "--root", str(root), "--db", str(db), "--doctor"],
                                capture_output=True, text=True, check=True)
        assert json.loads(result.stdout)["version"] == "0.1.2"

        connection = sqlite3.connect(db)
        try:
            versions = connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
            assert versions == [("001_foundation",), ("002_journal_request_scope",)]
            connection.execute("""INSERT INTO journal(investigation_id,kind,content,request_key)
                                VALUES(2,'note','Outro contexto','shared-key')""")
            try:
                connection.execute("""INSERT INTO journal(investigation_id,kind,content,request_key)
                                    VALUES(1,'note','Duplicado','shared-key')""")
            except sqlite3.IntegrityError:
                pass
            else:
                raise AssertionError("request_key deveria ser unica dentro da investigacao")
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
            connection.execute("UPDATE schema_migrations SET sha256='invalid' WHERE version='001_foundation'")
            connection.commit()
        finally:
            connection.close()

        rejected = subprocess.run([exe, "--root", str(root), "--db", str(db), "--doctor"],
                                  capture_output=True, text=True)
        assert rejected.returncode == 1
        assert "alterada apos aplicacao" in rejected.stderr
        print("OK: upgrade v0.1.0, ordem, escopo de idempotencia e hash historico")


if __name__ == "__main__":
    main()
