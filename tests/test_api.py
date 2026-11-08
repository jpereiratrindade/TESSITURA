#!/usr/bin/env python3
"""Teste local fim a fim, sem rede externa. Banco temporario descartavel."""
import json
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    exe, root = sys.argv[1:3]
    with tempfile.TemporaryDirectory(prefix="tessitura-test-") as tmp:
        db = str(Path(tmp) / "data.sqlite3")
        port = free_port()
        process = subprocess.Popen([exe, "--root", root, "--db", db, "--port", str(port)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        base = f"http://127.0.0.1:{port}"
        def req(path, data=None, expected=200):
            body = json.dumps(data).encode() if data is not None else None
            request = urllib.request.Request(base + path, data=body,
                                             headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    status = response.status
                    content = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                content = exc.read()
            assert status == expected, (path, status, expected, content[:400])
            return json.loads(content)
        try:
            for _ in range(60):
                try:
                    h = req("/api/health")
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(.1)
            else:
                raise AssertionError("Servidor nao iniciou")
            assert h["bind"] == "127.0.0.1"
            assert h["version"] == "0.1.4"
            caps = req("/api/v1/capabilities")
            assert caps["exposure"] == "local_only"
            assert caps["automated_inference"] is False
            assert caps["scientific_validation"] is False
            assert caps["published_investigations"] is True
            assert caps["observation_intervals"] is True
            experiment = req("/api/v1/investigations/published/exp-001")
            assert experiment["experiment_id"] == "EXP-001"
            assert experiment["compatibility"]["overall"] == "contextual_only"
            assert experiment["compatibility"]["causal_claim"] is False
            assert experiment["metrics"]["inmet"]["valid_hours"] == 744
            assert req("/api/v1/summary")["evidence"] == 0
            record = {"kind": "meteorological_alert", "source_name": "  INMET (fixture local)  ",
                      "source_ref": "TEST-AVISO-1", "statement": "Aviso declarado, sem ocorrencia confirmada.",
                      "location_ref": "4301602", "valid_start": "2026-11-08",
                      "valid_end": "2026-11-09", "observed_at": "2026-11-08T10:30:00-03:00",
                      "provenance_uri": "https://example.invalid/teste", "source_sha256": "A" * 64}
            assert req("/api/v1/evidence", {**record, "source_sha256": "INVALID"}, 400)["error"] == "invalid_input"
            assert req("/api/v1/evidence", {**record, "valid_start": "2026-02-30"}, 400)["error"] == "invalid_input"
            assert req("/api/v1/evidence", {**record, "valid_end": "2026-11-09T00:00:00Z"}, 400)["error"] == "invalid_input"
            assert req("/api/v1/evidence", {**record, "observed_start": "2026-11-08T10:00:00Z",
                       "observed_end": "2026-11-08T11:00:00Z"}, 400)["error"] == "invalid_input"
            first = req("/api/v1/evidence", record, 201)
            assert first["created"] is True
            canonical = {**record, "source_name": "INMET (fixture local)", "source_sha256": "a" * 64}
            same = req("/api/v1/evidence", canonical, 201)
            assert same["created"] is False and same["id"] == first["id"]
            evidence = req("/api/v1/evidence")["items"]
            assert len(evidence) == 1 and evidence[0]["validation_status"] == "not_validated"
            assert evidence[0]["source_name"] == "INMET (fixture local)"
            assert evidence[0]["source_sha256"] == "a" * 64
            assert evidence[0]["observed_at"] == record["observed_at"]
            assert evidence[0]["observed_start"] == "" and evidence[0]["observed_end"] == ""
            inv = req("/api/v1/investigations", {"title": "Trajetorias hipoteticas",
                  "question": "Quais evidencias e limitacoes existem?", "location_ref": "4301602"}, 201)
            inv_id = inv["id"]
            link = {"evidence_id": first["id"], "relation": "contextualizes",
                    "justification": "Registro documental de aviso, nao ocorrencia."}
            assert req(f"/api/v1/investigations/{inv_id}/links", link, 201)["created"] is True
            assert req(f"/api/v1/investigations/{inv_id}/links", link, 201)["created"] is False
            diary = {"kind": "objection", "content": "Aviso nao comprova evento.", "request_key": "test-001"}
            assert req(f"/api/v1/investigations/{inv_id}/journal", diary, 201)["created"] is True
            assert req(f"/api/v1/investigations/{inv_id}/journal", diary, 201)["created"] is False
            assert req(f"/api/v1/investigations/{inv_id}/journal", {**diary, "content":"Alterado"}, 400)["error"] == "invalid_input"
            inv2 = req("/api/v1/investigations", {"title": "Investigacao paralela",
                       "question": "A mesma chave pode existir em outro contexto?"}, 201)
            assert req(f"/api/v1/investigations/{inv2['id']}/journal", diary, 201)["created"] is True
            dossier = req(f"/api/v1/investigations/{inv_id}")
            assert len(dossier["evidence_links"]) == 1 and len(dossier["journal"]) == 1
            assert req("/api/v1/summary")["links"] == 1
            assert len(req("/api/v1/audit")["items"]) >= 4
            assert req("/api/v1/evidence", {"kind": "other", "source_name": "x",
                       "source_ref": "x", "statement": "x" * 70000}, 413)["error"] == "payload_too_large"
            with urllib.request.urlopen(base + "/", timeout=3) as r:
                page = r.read()
                assert b'TESSITURA' in page and b'observed_at' in page
                assert b'ADAPTABRASIL' in page and b'EVIDA' in page
                assert b'Adaptador contratual offline' in page
            with urllib.request.urlopen(base + "/style.css", timeout=3) as r:
                assert b'--navy:' in r.read()
            con = sqlite3.connect(db)
            try:
                try:
                    con.execute("UPDATE evidence SET statement='ALTERADO' WHERE id=?", (first["id"],))
                except sqlite3.DatabaseError as exc:
                    assert "append-only" in str(exc)
                else:
                    raise AssertionError("Evidencia deveria ser imutavel")
                assert con.execute("PRAGMA foreign_key_check").fetchall() == []
                assert con.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 3
            finally:
                con.close()
            print("OK: HTTP, persistencia, idempotencia, integridade, diario e limite epistêmico")
        finally:
            process.terminate()
            try:
                process.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        # Nova abertura do banco valida a persistência e o hash da migração.
        result = subprocess.run([exe, "--root", root, "--db", db, "--doctor"],
                                capture_output=True, text=True, check=True)
        persisted = json.loads(result.stdout)
        assert persisted["evidence"] == 1
        assert persisted["investigations"] == 2
        assert persisted["journal"] == 2


if __name__ == "__main__":
    main()
