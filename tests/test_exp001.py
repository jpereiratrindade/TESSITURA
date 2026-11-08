#!/usr/bin/env python3
"""Executa duas vezes a integração real pequena do EXP-001."""
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def execute(adapter, server, root, database, output):
    result = subprocess.run(
        [sys.executable, str(adapter), "run", "--root", str(root), "--server", str(server),
         "--db", str(database), "--output", str(output)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def main():
    server_arg, root_arg = sys.argv[1:3]
    server = Path(server_arg).resolve()
    root = Path(root_arg).resolve()
    adapter = root / "tools/exp001.py"
    with tempfile.TemporaryDirectory(prefix="tessitura-exp001-") as temporary:
        base = Path(temporary)
        database = base / "exp001.sqlite3"
        output = base / "output"

        first = execute(adapter, server, root, database, output)
        assert first["experiment"] == "EXP-001"
        assert first["compatibility"] == "contextual_only"
        assert first["execution"]["first_evidence_created"] == 2
        assert first["execution"]["second_evidence_created"] == 0
        assert first["execution"]["second_links_created"] == 0
        assert first["execution"]["second_journal_created"] == 0

        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        assert report["compatibility"]["spatial"]["status"] == "not_directly_comparable"
        assert report["compatibility"]["causal_claim"] is False
        assert report["metrics"]["inmet"]["valid_hours"] == 744
        assert report["metrics"]["mapbiomas"]["class_count"] == 13
        dossier = (output / "dossier.md").read_text(encoding="utf-8")
        assert "contextual_only" in dossier and "não demonstra associação estatística" in dossier

        second = execute(adapter, server, root, database, output)
        assert second["execution"]["first_evidence_created"] == 0
        assert second["execution"]["first_links_created"] == 0
        assert second["execution"]["first_journal_created"] == 0

        connection = sqlite3.connect(database)
        try:
            counts = tuple(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                           for table in ("evidence", "investigations", "evidence_links", "journal"))
            assert counts == (2, 1, 2, 3)
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            connection.close()
        print("OK: fontes reais, contrato, compatibilidade, dossie e repetibilidade EXP-001")


if __name__ == "__main__":
    main()
