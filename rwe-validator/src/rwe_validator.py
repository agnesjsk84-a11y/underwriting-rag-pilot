#!/usr/bin/env python3
"""Configuration-driven CSV quality validator for RWE datasets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    row: int | None = None
    column: str | None = None
    value: str | None = None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_value(value: str, rule: dict[str, Any]) -> Any:
    value_type = rule.get("type", "string")
    if value_type == "string":
        return value
    if value_type == "integer":
        return int(value)
    if value_type == "number":
        return float(value)
    if value_type == "date":
        return datetime.strptime(value, rule.get("format", "%Y-%m-%d"))
    raise ValueError(f"지원하지 않는 자료형: {value_type}")


def validate_rows(
    fieldnames: list[str], rows: list[dict[str, str]], config: dict[str, Any]
) -> list[Finding]:
    findings: list[Finding] = []
    defined_columns = {rule["name"] for rule in config.get("columns", [])}

    for name in sorted(defined_columns - set(fieldnames)):
        rule = next(item for item in config["columns"] if item["name"] == name)
        findings.append(
            Finding(
                rule_id=f"schema.column.{name}",
                severity=rule.get("severity", "error"),
                message=f"필수 검증 컬럼이 입력 파일에 없습니다: {name}",
                column=name,
            )
        )

    for row_number, row in enumerate(rows, start=2):
        for rule in config.get("columns", []):
            name = rule["name"]
            if name not in fieldnames:
                continue
            raw_value = (row.get(name) or "").strip()
            severity = rule.get("severity", "error")

            if not raw_value:
                if rule.get("required", False):
                    findings.append(
                        Finding(
                            rule_id=f"column.{name}.required",
                            severity=severity,
                            message="필수값이 누락되었습니다.",
                            row=row_number,
                            column=name,
                            value=raw_value,
                        )
                    )
                continue

            try:
                parsed = parse_value(raw_value, rule)
            except (ValueError, TypeError) as exc:
                findings.append(
                    Finding(
                        rule_id=f"column.{name}.type",
                        severity=severity,
                        message=f"자료형 또는 형식이 올바르지 않습니다: {exc}",
                        row=row_number,
                        column=name,
                        value=raw_value,
                    )
                )
                continue

            if "allowed_values" in rule and raw_value not in rule["allowed_values"]:
                findings.append(
                    Finding(
                        rule_id=f"column.{name}.allowed_values",
                        severity=severity,
                        message="허용된 코드 목록에 없는 값입니다.",
                        row=row_number,
                        column=name,
                        value=raw_value,
                    )
                )

            if isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
                if "min" in rule and parsed < rule["min"]:
                    findings.append(
                        Finding(
                            rule_id=f"column.{name}.min",
                            severity=severity,
                            message=f"최솟값 {rule['min']}보다 작습니다.",
                            row=row_number,
                            column=name,
                            value=raw_value,
                        )
                    )
                if "max" in rule and parsed > rule["max"]:
                    findings.append(
                        Finding(
                            rule_id=f"column.{name}.max",
                            severity=severity,
                            message=f"최댓값 {rule['max']}보다 큽니다.",
                            row=row_number,
                            column=name,
                            value=raw_value,
                        )
                    )

        for rule in config.get("date_order_rules", []):
            start_raw = (row.get(rule["start"]) or "").strip()
            end_raw = (row.get(rule["end"]) or "").strip()
            if not start_raw or not end_raw:
                continue
            try:
                date_format = rule.get("format", "%Y-%m-%d")
                start = datetime.strptime(start_raw, date_format)
                end = datetime.strptime(end_raw, date_format)
            except ValueError:
                continue
            if end < start:
                findings.append(
                    Finding(
                        rule_id=f"date_order.{rule['name']}",
                        severity=rule.get("severity", "error"),
                        message=f"{rule['end']} 값이 {rule['start']}보다 빠릅니다.",
                        row=row_number,
                        column=rule["end"],
                        value=end_raw,
                    )
                )

    for rule in config.get("unique_keys", []):
        columns = rule["columns"]
        if any(column not in fieldnames for column in columns):
            continue
        keys: dict[tuple[str, ...], list[int]] = {}
        for row_number, row in enumerate(rows, start=2):
            key = tuple((row.get(column) or "").strip() for column in columns)
            if any(not value for value in key):
                continue
            keys.setdefault(key, []).append(row_number)
        for key, row_numbers in keys.items():
            if len(row_numbers) > 1:
                findings.append(
                    Finding(
                        rule_id=f"unique.{rule['name']}",
                        severity=rule.get("severity", "error"),
                        message=f"복합키가 중복되었습니다. 행: {row_numbers}",
                        row=row_numbers[0],
                        column=",".join(columns),
                        value="|".join(key),
                    )
                )

    return findings


def build_report(
    input_path: Path,
    config_path: Path,
    rows: list[dict[str, str]],
    findings: list[Finding],
    config: dict[str, Any],
) -> dict[str, Any]:
    counts = Counter(finding.severity for finding in findings)
    status = "fail" if counts["error"] else "pass_with_warnings" if counts["warning"] else "pass"
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": config.get("dataset", input_path.stem),
        "dataset_rule_version": config.get("version", "unknown"),
        "status": status,
        "input": {
            "path": str(input_path),
            "sha256": file_sha256(input_path),
            "row_count": len(rows),
        },
        "rules": {
            "path": str(config_path),
            "sha256": file_sha256(config_path),
        },
        "summary": {
            "total_findings": len(findings),
            "errors": counts["error"],
            "warnings": counts["warning"],
        },
        "findings": [asdict(finding) for finding in findings],
    }


def report_to_markdown(report: dict[str, Any]) -> str:
    status_label = {
        "pass": "승인 가능",
        "pass_with_warnings": "경고 검토 필요",
        "fail": "반려",
    }[report["status"]]
    lines = [
        "# RWE 데이터 검증 리포트",
        "",
        f"- 판정: **{status_label}** (`{report['status']}`)",
        f"- 데이터셋: `{report['dataset']}`",
        f"- 규칙 버전: `{report['dataset_rule_version']}`",
        f"- 레코드 수: {report['input']['row_count']}",
        f"- 오류: {report['summary']['errors']}",
        f"- 경고: {report['summary']['warnings']}",
        f"- 입력 SHA-256: `{report['input']['sha256']}`",
        f"- 규칙 SHA-256: `{report['rules']['sha256']}`",
        "",
        "## 검증 결과",
        "",
    ]
    if not report["findings"]:
        lines.append("검출된 오류 또는 경고가 없습니다.")
    else:
        lines.extend(
            [
                "| 심각도 | 규칙 | 행 | 컬럼 | 값 | 설명 |",
                "|---|---|---:|---|---|---|",
            ]
        )
        for finding in report["findings"]:
            values = [
                finding["severity"],
                finding["rule_id"],
                finding["row"] or "",
                finding["column"] or "",
                finding["value"] or "",
                finding["message"],
            ]
            escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
            lines.append("| " + " | ".join(escaped) + " |")
    lines.extend(["", "_자동 생성된 검증 근거자료입니다._", ""])
    return "\n".join(lines)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("CSV 헤더가 없습니다.")
        return reader.fieldnames, list(reader)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RWE CSV 데이터 품질 검증")
    parser.add_argument("--input", required=True, type=Path, help="검증할 CSV")
    parser.add_argument("--rules", required=True, type=Path, help="JSON 규칙 파일")
    parser.add_argument("--output-json", type=Path, help="JSON 리포트 경로")
    parser.add_argument("--output-md", type=Path, help="Markdown 리포트 경로")
    args = parser.parse_args(argv)

    try:
        config = json.loads(args.rules.read_text(encoding="utf-8"))
        fieldnames, rows = load_csv(args.input)
        findings = validate_rows(fieldnames, rows, config)
        report = build_report(args.input, args.rules, rows, findings, config)
        if args.output_json:
            write_text(args.output_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        if args.output_md:
            write_text(args.output_md, report_to_markdown(report))
        print(json.dumps(report["summary"] | {"status": report["status"]}, ensure_ascii=False))
        return 1 if report["status"] == "fail" else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"검증 실행 오류: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
