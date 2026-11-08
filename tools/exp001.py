#!/usr/bin/env python3
"""EXP-001: integração mínima MapBiomas + INMET sem inferência causal."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from xml.etree.ElementTree import iterparse
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ADAPTER_VERSION = "exp001-adapter/1.0.0"
EXPERIMENT_ID = "EXP-001"
INVESTIGATION_TITLE = "EXP-001 · Bagé 2023 · cobertura e meteorologia"
INVESTIGATION_QUESTION = (
    "Quais classes de cobertura e uso da terra são mapeadas para Bagé em 2023 e quais "
    "condições de temperatura e precipitação foram observadas pela estação A827 em janeiro; "
    "essas descrições podem ser diretamente comparadas?"
)
RECORD_PATHS = (
    "data/exp001/records/mapbiomas_bage_2023.json",
    "data/exp001/records/inmet_a827_2023-01.json",
)
INVALID_FIXTURE = "data/exp001/fixtures/invalid_missing_as_zero.json"
MAPBIOMAS_ARCHIVE_SHA256 = "c223fd84dcdd21e49d651788ff5a726a7e3aa04d2eab730e99407dd80a8d3e30"
MAPBIOMAS_MEMBER_SHA256 = "8de70a35fdd35f943e059763d128825ee08c0978948311ac03c769e0f178abfe"
MAPBIOMAS_SUBSET_SHA256 = "1822832e28324a93293eebeb715681a3624287626e37184e76168b7440de6da8"
INMET_ARCHIVE_SHA256 = "b17391392cc1219151977cc2c46a7ab24368d821fd780311da9fff62a627bfd8"
INMET_MEMBER_SHA256 = "ad392c891037f90202e33a59c9b2c7138c0da242a4a6ffc42a4e3af9b807a438"
INMET_SUBSET_SHA256 = "bbf317ac87cfaa59720bedcb44eb33662b23b7ecd87edbd08b6798927c1d12de"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"Hash divergente para {label}: esperado {expected}, obtido {actual}")


def extract_mapbiomas(archive: Path, output: Path) -> Path:
    require_hash(archive, MAPBIOMAS_ARCHIVE_SHA256, "ZIP MapBiomas")
    member = "MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY.xlsx"
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with tempfile.TemporaryDirectory(prefix="tessitura-mapbiomas-") as temporary:
        temporary_path = Path(temporary)
        with zipfile.ZipFile(archive) as source_zip:
            source_zip.extract(member, temporary_path)
        workbook = temporary_path / member
        require_hash(workbook, MAPBIOMAS_MEMBER_SHA256, "XLSX MapBiomas")
        with zipfile.ZipFile(workbook) as spreadsheet:
            shared_strings = []
            for _, element in iterparse(spreadsheet.open("xl/sharedStrings.xml"), events=("end",)):
                if element.tag == namespace + "si":
                    shared_strings.append("".join(text.text or "" for text in element.iter(namespace + "t")))
                    element.clear()
            selected = []
            for _, element in iterparse(spreadsheet.open("xl/worksheets/sheet2.xml"), events=("end",)):
                if element.tag != namespace + "row":
                    continue
                cells = {}
                for cell in element.findall(namespace + "c"):
                    value_element = cell.find(namespace + "v")
                    value = "" if value_element is None else value_element.text
                    if cell.get("t") == "s" and value:
                        value = shared_strings[int(value)]
                    column = "".join(character for character in cell.get("r") if character.isalpha())
                    cells[column] = value
                if cells.get("F") == "4301602":
                    selected.append([cells.get(column, "") for column in ("B", "C", "D", "E", "F", "G", "I", "J", "K", "L", "M", "N", "BA")])
                element.clear()
    if len(selected) != 13:
        raise ValueError(f"Esperadas 13 classes MapBiomas para Bagé; obtidas {len(selected)}")
    target = output / "mapbiomas_bage_2023.csv"
    with target.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(("country", "biome", "region", "state", "geocode", "municipality", "class_id", "level_0", "level_1", "level_2", "level_3", "level_4", "area_ha"))
        writer.writerows(selected)
    require_hash(target, MAPBIOMAS_SUBSET_SHA256, "subconjunto MapBiomas")
    return target


def source_number(value: str) -> float | None:
    normalized = value.strip()
    if normalized in ("", "9999", "Null"):
        return None
    return float(normalized.replace(",", "."))


def extract_inmet(archive: Path, output: Path) -> Path:
    require_hash(archive, INMET_ARCHIVE_SHA256, "ZIP INMET")
    member = "INMET_S_RS_A827_BAGE_01-01-2023_A_31-12-2023.CSV"
    with zipfile.ZipFile(archive) as source_zip:
        raw = source_zip.read(member)
    if hashlib.sha256(raw).hexdigest() != INMET_MEMBER_SHA256:
        raise ValueError("Hash divergente para CSV A827 do INMET")
    source = io.StringIO(raw.decode("iso-8859-1"), newline="")
    for _ in range(8):
        next(source)
    rows = [row for row in csv.DictReader(source, delimiter=";") if row["Data"].startswith("2023/01/")]
    precipitation_key = "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"
    temperature_key = "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)"
    target = output / "inmet_a827_2023-01_daily.csv"
    with target.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(("date", "hours_expected", "hours_valid", "precipitation_mm", "temperature_mean_c", "temperature_min_c", "temperature_max_c"))
        for source_date in sorted({row["Data"] for row in rows}):
            daily = [row for row in rows if row["Data"] == source_date]
            precipitation = [source_number(row[precipitation_key]) for row in daily]
            temperature = [source_number(row[temperature_key]) for row in daily]
            precipitation = [value for value in precipitation if value is not None]
            temperature = [value for value in temperature if value is not None]
            writer.writerow((
                source_date.replace("/", "-"), 24, min(len(precipitation), len(temperature)),
                f"{sum(precipitation):.1f}", f"{sum(temperature) / len(temperature):.6f}",
                f"{min(temperature):.1f}", f"{max(temperature):.1f}",
            ))
    require_hash(target, INMET_SUBSET_SHA256, "subconjunto INMET")
    return target


def prepare_sources(mapbiomas_archive: Path, inmet_archive: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    mapbiomas = extract_mapbiomas(mapbiomas_archive, output)
    inmet = extract_inmet(inmet_archive, output)
    return {"mapbiomas": str(mapbiomas), "inmet": str(inmet), "hashes_verified": True}


def validate_contracts(root: Path) -> list[dict]:
    schema = read_json(root / "contracts/integration-record-v1.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    records = []
    for relative_path in RECORD_PATHS:
        record = read_json(root / relative_path)
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise ValueError(f"Contrato inválido em {relative_path}: {details}")
        quality = record["quality"]
        if quality["valid_count"] + quality["missing_count"] != quality["expected_count"]:
            raise ValueError(f"Contagens de qualidade inconsistentes em {relative_path}")
        sample = root / record["provenance"]["sample_path"]
        actual_hash = sha256_file(sample)
        if actual_hash != record["provenance"]["subset_sha256"]:
            raise ValueError(f"Hash do subconjunto divergente: {sample}")
        if record["provenance"]["adapter_version"] != ADAPTER_VERSION:
            raise ValueError(f"Versão de adaptador divergente em {relative_path}")
        records.append(record)

    invalid = read_json(root / INVALID_FIXTURE)
    if not list(validator.iter_errors(invalid)):
        raise ValueError("Fixture missing-as-zero deveria ser rejeitada")
    return records


def close_enough(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
    return abs(actual - expected) <= tolerance * max(1.0, abs(actual), abs(expected))


def analyze_mapbiomas(root: Path, record: dict) -> dict:
    sample = root / record["provenance"]["sample_path"]
    with sample.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows or any(row["geocode"] != "4301602" for row in rows):
        raise ValueError("Subconjunto MapBiomas não está restrito ao geocódigo 4301602")
    areas = [float(row["area_ha"]) for row in rows]
    total_area = sum(areas)
    expected = record["data"]
    if len(rows) != expected["class_count"] or not close_enough(total_area, expected["total_area_ha"]):
        raise ValueError("Métricas MapBiomas divergentes do registro contratado")
    top_classes = sorted(
        ({"class_id": int(row["class_id"]), "class": row["level_4"], "area_ha": float(row["area_ha"])} for row in rows),
        key=lambda item: item["area_ha"],
        reverse=True,
    )[:5]
    for item in top_classes:
        item["share_percent"] = item["area_ha"] / total_area * 100
    return {"class_count": len(rows), "total_area_ha": total_area, "top_classes": top_classes}


def analyze_inmet(root: Path, record: dict) -> dict:
    sample = root / record["provenance"]["sample_path"]
    with sample.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    expected_hours = sum(int(row["hours_expected"]) for row in rows)
    valid_hours = sum(int(row["hours_valid"]) for row in rows)
    precipitation = sum(float(row["precipitation_mm"]) for row in rows)
    weighted_temperature = sum(float(row["temperature_mean_c"]) * int(row["hours_valid"]) for row in rows)
    temperature_mean = weighted_temperature / valid_hours
    temperature_min = min(float(row["temperature_min_c"]) for row in rows)
    temperature_max = max(float(row["temperature_max_c"]) for row in rows)
    expected = record["data"]
    checks = (
        len(rows) == expected["days"],
        expected_hours == record["quality"]["expected_count"],
        valid_hours == record["quality"]["valid_count"],
        close_enough(precipitation, expected["precipitation_total_mm"]),
        close_enough(temperature_mean, expected["temperature_mean_c"]),
        close_enough(temperature_min, expected["temperature_min_c"]),
        close_enough(temperature_max, expected["temperature_max_c"]),
    )
    if not all(checks):
        raise ValueError("Métricas INMET divergentes do registro contratado")
    return {
        "days": len(rows),
        "expected_hours": expected_hours,
        "valid_hours": valid_hours,
        "missing_hours": expected_hours - valid_hours,
        "precipitation_total_mm": precipitation,
        "temperature_mean_c": temperature_mean,
        "temperature_min_c": temperature_min,
        "temperature_max_c": temperature_max,
    }


def analyze(root: Path) -> dict:
    records = validate_contracts(root)
    by_system = {record["identity"]["source_system"]: record for record in records}
    mapbiomas = analyze_mapbiomas(root, by_system["MapBiomas Brasil"])
    inmet = analyze_inmet(root, by_system["INMET"])
    return {
        "experiment_id": EXPERIMENT_ID,
        "adapter_version": ADAPTER_VERSION,
        "records": [record["record_id"] for record in records],
        "operations": [
            {
                "id": "mapbiomas-select-geocode-year-v1",
                "input": by_system["MapBiomas Brasil"]["provenance"]["source_member_sha256"],
                "parameters": {"geocode": "4301602", "year_column": "y2023"},
                "output": by_system["MapBiomas Brasil"]["provenance"]["subset_sha256"],
            },
            {
                "id": "inmet-hourly-to-daily-v1",
                "input": by_system["INMET"]["provenance"]["source_member_sha256"],
                "parameters": {
                    "station": "A827",
                    "period": "2023-01-01/2023-01-31",
                    "timezone": "UTC",
                    "missing_markers": ["", "9999", "Null"],
                    "precipitation": "sum",
                    "temperature": ["mean", "min", "max"],
                },
                "output": by_system["INMET"]["provenance"]["subset_sha256"],
            },
        ],
        "metrics": {"mapbiomas": mapbiomas, "inmet": inmet},
        "compatibility": {
            "temporal": {
                "status": "overlap_with_granularity_mismatch",
                "detail": "janeiro de 2023 está dentro do mapa anual de 2023, mas horário/dia e ano não são granularidades equivalentes",
            },
            "spatial": {
                "status": "not_directly_comparable",
                "detail": "estatística do polígono municipal e medição pontual A827 possuem suportes espaciais distintos",
            },
            "overall": "contextual_only",
            "causal_claim": False,
        },
        "conclusion": (
            "As duas fontes podem coexistir no mesmo dossiê como contexto documentado, mas este recorte não autoriza "
            "comparação espacial direta, associação estatística ou explicação causal entre cobertura e meteorologia."
        ),
    }


def api(base_url: str, path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        base_url + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"API {path}: HTTP {error.code}: {detail}") from error


def find_or_create_investigation(base_url: str) -> tuple[int, bool]:
    for item in api(base_url, "/api/v1/investigations")["items"]:
        if (
            item["title"] == INVESTIGATION_TITLE
            and item["question"] == INVESTIGATION_QUESTION
            and item["location_ref"] == "IBGE:4301602"
        ):
            return item["id"], False
    created = api(
        base_url,
        "/api/v1/investigations",
        {
            "title": INVESTIGATION_TITLE,
            "question": INVESTIGATION_QUESTION,
            "location_ref": "IBGE:4301602",
            "valid_start": "2023-01-01",
            "valid_end": "2023-12-31",
        },
    )
    return created["id"], True


def register_once(base_url: str, root: Path, analysis: dict) -> dict:
    records = {read_json(root / path)["identity"]["source_system"]: read_json(root / path) for path in RECORD_PATHS}
    map_metric = analysis["metrics"]["mapbiomas"]
    inmet_metric = analysis["metrics"]["inmet"]
    evidence_payloads = (
        {
            "kind": "land_cover_classification",
            "source_name": "Projeto MapBiomas — Coleção 11",
            "source_ref": records["MapBiomas Brasil"]["record_id"],
            "statement": (
                f"A tabela municipal da Coleção 11 registra {map_metric['class_count']} classes e "
                f"{map_metric['total_area_ha']:.3f} ha para Bagé/RS em 2023. Trata-se de estatística de "
                "classificação anual, não de observação direta de processo."
            ),
            "location_ref": "IBGE:4301602 (polígono municipal)",
            "valid_start": "2023-01-01",
            "valid_end": "2023-12-31",
            "provenance_uri": records["MapBiomas Brasil"]["provenance"]["source_uri"],
            "source_sha256": records["MapBiomas Brasil"]["provenance"]["subset_sha256"],
        },
        {
            "kind": "derived_indicator",
            "source_name": "INMET A827 via TESSITURA EXP-001",
            "source_ref": records["INMET"]["record_id"],
            "statement": (
                f"Agregação determinística de {inmet_metric['valid_hours']} observações horárias brutas "
                f"da estação A827 em janeiro de 2023: precipitação {inmet_metric['precipitation_total_mm']:.1f} mm; "
                f"temperatura média {inmet_metric['temperature_mean_c']:.3f} °C, mínima "
                f"{inmet_metric['temperature_min_c']:.1f} °C e máxima {inmet_metric['temperature_max_c']:.1f} °C. "
                "O INMET informa que dados automáticos são brutos e não validados."
            ),
            "location_ref": "INMET:A827 (-31.34777777,-54.01333333; ponto)",
            "valid_start": "2023-01-01",
            "valid_end": "2023-01-31",
            "observed_start": "2023-01-01T00:00:00Z",
            "observed_end": "2023-01-31T23:00:00Z",
            "provenance_uri": records["INMET"]["provenance"]["source_uri"],
            "source_sha256": records["INMET"]["provenance"]["subset_sha256"],
        },
    )
    evidence_results = [api(base_url, "/api/v1/evidence", payload) for payload in evidence_payloads]
    investigation_id, investigation_created = find_or_create_investigation(base_url)
    justifications = (
        "Documenta a classificação anual do município; não atribui processo nem causa às classes.",
        "Documenta condições na estação A827; o ponto não representa automaticamente o município.",
    )
    links = [
        api(
            base_url,
            f"/api/v1/investigations/{investigation_id}/links",
            {"evidence_id": evidence["id"], "relation": "contextualizes", "justification": justification},
        )
        for evidence, justification in zip(evidence_results, justifications)
    ]
    journal_payloads = (
        {
            "kind": "question",
            "content": INVESTIGATION_QUESTION,
            "request_key": "exp001-question-v1",
        },
        {
            "kind": "objection",
            "content": (
                "A estação A827 é suporte pontual e a tabela MapBiomas agrega o polígono municipal; "
                "coincidência temporal não torna esses suportes equivalentes."
            ),
            "request_key": "exp001-spatial-objection-v1",
        },
        {
            "kind": "decision",
            "content": (
                "Resultado da operação de compatibilidade: contextual_only. Não executar correlação, "
                "atribuição causal ou generalização da estação para Bagé neste experimento."
            ),
            "request_key": "exp001-compatibility-decision-v1",
        },
    )
    journal = [
        api(base_url, f"/api/v1/investigations/{investigation_id}/journal", payload)
        for payload in journal_payloads
    ]
    return {
        "investigation_id": investigation_id,
        "investigation_created": investigation_created,
        "evidence": evidence_results,
        "links": links,
        "journal": journal,
        "summary": api(base_url, "/api/v1/summary"),
    }


def dossier_markdown(analysis: dict, execution: dict) -> str:
    map_metric = analysis["metrics"]["mapbiomas"]
    inmet_metric = analysis["metrics"]["inmet"]
    top_lines = "\n".join(
        f"- Classe {item['class_id']} — {item['class']}: {item['area_ha']:.3f} ha ({item['share_percent']:.2f}%)."
        for item in map_metric["top_classes"]
    )
    summary_text = json.dumps(execution["summary"], ensure_ascii=False, sort_keys=True)
    return f"""# EXP-001 — Dossiê reproduzível

**Pergunta:** {INVESTIGATION_QUESTION}

## Fontes e operações

- MapBiomas Brasil, Coleção 11 v1: seleção do município IBGE 4301602 e ano 2023; hash do subconjunto `{execution['mapbiomas_subset_sha256']}`.
- INMET, estação automática A827: agregação de observações horárias de janeiro de 2023; hash do subconjunto `{execution['inmet_subset_sha256']}`.
- Adaptador: `{ADAPTER_VERSION}`. Nenhum valor ausente foi convertido em zero.

## Resultados verificáveis

- MapBiomas: {map_metric['class_count']} classes, área tabulada total de {map_metric['total_area_ha']:.3f} ha.
{top_lines}
- INMET: {inmet_metric['valid_hours']}/{inmet_metric['expected_hours']} observações horárias válidas; precipitação total de {inmet_metric['precipitation_total_mm']:.1f} mm; temperatura média de {inmet_metric['temperature_mean_c']:.3f} °C, mínima de {inmet_metric['temperature_min_c']:.1f} °C e máxima de {inmet_metric['temperature_max_c']:.1f} °C.

## Compatibilidade

- Temporal: `{analysis['compatibility']['temporal']['status']}` — {analysis['compatibility']['temporal']['detail']}.
- Espacial: `{analysis['compatibility']['spatial']['status']}` — {analysis['compatibility']['spatial']['detail']}.
- Resultado global: `{analysis['compatibility']['overall']}`.

## Conclusão e objeção preservada

{analysis['conclusion']}

A classificação é anual e municipal; a observação meteorológica é horária e pontual. Este dossiê não demonstra associação estatística, influência, causalidade ou representatividade da estação para todo o território.

## Repetibilidade

- Investigação TESSITURA: #{execution['investigation_id']}.
- Primeira passagem: evidências criadas `{execution['first_evidence_created']}`, vínculos criados `{execution['first_links_created']}`, diário criado `{execution['first_journal_created']}`.
- Segunda passagem: evidências criadas `{execution['second_evidence_created']}`, vínculos criados `{execution['second_links_created']}`, diário criado `{execution['second_journal_created']}`.
- Contagens finais: `{summary_text}`.
"""


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def run_experiment(root: Path, server: Path, database: Path, output: Path) -> dict:
    analysis = analyze(root)
    database.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    port = free_port()
    process = subprocess.Popen(
        [str(server), "--root", str(root), "--db", str(database), "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            if process.poll() is not None:
                raise RuntimeError(process.stderr.read())
            try:
                api(base_url, "/api/health")
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.05)
        else:
            raise RuntimeError("Servidor TESSITURA não iniciou")
        first = register_once(base_url, root, analysis)
        second = register_once(base_url, root, analysis)
        if second["summary"] != first["summary"]:
            raise RuntimeError("Reexecução alterou contagens lógicas")
        if any(item["created"] for item in second["evidence"] + second["links"] + second["journal"]):
            raise RuntimeError("Reexecução duplicou registros idempotentes")
        if second["investigation_created"]:
            raise RuntimeError("Reexecução duplicou a investigação")
        records = {read_json(root / path)["identity"]["source_system"]: read_json(root / path) for path in RECORD_PATHS}
        execution = {
            "investigation_id": second["investigation_id"],
            "mapbiomas_subset_sha256": records["MapBiomas Brasil"]["provenance"]["subset_sha256"],
            "inmet_subset_sha256": records["INMET"]["provenance"]["subset_sha256"],
            "first_evidence_created": sum(item["created"] for item in first["evidence"]),
            "first_links_created": sum(item["created"] for item in first["links"]),
            "first_journal_created": sum(item["created"] for item in first["journal"]),
            "second_evidence_created": sum(item["created"] for item in second["evidence"]),
            "second_links_created": sum(item["created"] for item in second["links"]),
            "second_journal_created": sum(item["created"] for item in second["journal"]),
            "summary": second["summary"],
        }
        report = {**analysis, "execution": execution}
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "dossier.md").write_text(dossier_markdown(analysis, execution), encoding="utf-8")
        return report
    finally:
        process.terminate()
        try:
            process.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "validate", "analyze", "run"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--server", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mapbiomas-archive", type=Path)
    parser.add_argument("--inmet-archive", type=Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.command == "prepare":
        if not arguments.mapbiomas_archive or not arguments.inmet_archive or not arguments.output:
            parser.error("prepare exige --mapbiomas-archive, --inmet-archive e --output")
        prepared = prepare_sources(arguments.mapbiomas_archive.resolve(), arguments.inmet_archive.resolve(), arguments.output.resolve())
        print(json.dumps(prepared, ensure_ascii=False))
        return
    if arguments.command == "validate":
        records = validate_contracts(root)
        print(json.dumps({"valid_records": [record["record_id"] for record in records], "invalid_fixture_rejected": True}, ensure_ascii=False))
        return
    if arguments.command == "analyze":
        print(json.dumps(analyze(root), ensure_ascii=False, indent=2))
        return
    if not arguments.server or not arguments.db or not arguments.output:
        parser.error("run exige --server, --db e --output")
    report = run_experiment(root, arguments.server.resolve(), arguments.db.resolve(), arguments.output.resolve())
    print(json.dumps({"experiment": report["experiment_id"], "compatibility": report["compatibility"]["overall"], "execution": report["execution"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
