#!/usr/bin/env python3
"""Audit OHLC candle CSV files for HydraAI research.

Standard-library only. This module never repairs or silently drops source rows.
It writes a reproducible JSON report and optionally a row-level issue CSV.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALIASES = {
    "timestamp": ("timestamp", "time", "datetime", "date", "time_utc", "open_time"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol", "v", "tick_volume"),
}


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _parse_timestamp(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("empty timestamp")
    # Numeric timestamps: infer seconds vs milliseconds by magnitude.
    if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        number = float(raw)
        if abs(number) >= 100_000_000_000:
            number /= 1000.0
        return datetime.fromtimestamp(number, tz=timezone.utc)
    candidate = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(candidate)
    if dt.tzinfo is None:
        # Naive timestamps are treated as UTC, but explicitly flagged in report.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_columns(headers: list[str]) -> dict[str, str]:
    normalized = {_norm(h): h for h in headers}
    found: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if _norm(alias) in normalized:
                found[field] = normalized[_norm(alias)]
                break
    missing = [name for name in ("timestamp", "open", "high", "low", "close") if name not in found]
    if missing:
        raise ValueError(
            "Missing required OHLC columns: " + ", ".join(missing)
            + ". Recognized headers: " + ", ".join(headers)
        )
    return found


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_csv(path: Path, expected_interval_seconds: int = 60) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    issues: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    naive_timestamp_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        columns = _resolve_columns(reader.fieldnames)
        for line_number, raw in enumerate(reader, start=2):
            try:
                raw_time = (raw.get(columns["timestamp"]) or "").strip()
                if raw_time and not re.search(r"(Z|[+-]\d\d:\d\d)$", raw_time) and not re.fullmatch(r"-?\d+(?:\.\d+)?", raw_time):
                    naive_timestamp_count += 1
                stamp = _parse_timestamp(raw_time)
                values = {key: float(raw[columns[key]]) for key in ("open", "high", "low", "close")}
                if not all(math.isfinite(v) for v in values.values()):
                    raise ValueError("non-finite OHLC value")
                row = {"timestamp": stamp, **values, "line": line_number}
                rows.append(row)
            except Exception as exc:
                issues.append({"line": line_number, "type": "parse_error", "detail": str(exc)})

    if not rows:
        raise ValueError("No valid candle rows could be parsed")

    counts = Counter(row["timestamp"] for row in rows)
    duplicate_stamps = sorted(stamp for stamp, count in counts.items() if count > 1)
    invalid_ohlc = []
    flat = 0
    for row in rows:
        o, h, l, c = (row[k] for k in ("open", "high", "low", "close"))
        reasons = []
        if min(o, h, l, c) <= 0:
            reasons.append("non_positive_price")
        if h < max(o, c, l):
            reasons.append("high_below_component")
        if l > min(o, c, h):
            reasons.append("low_above_component")
        if h < l:
            reasons.append("high_below_low")
        if reasons:
            invalid_ohlc.append({"line": row["line"], "timestamp": row["timestamp"].isoformat(), "reasons": reasons})
            issues.append({"line": row["line"], "type": "invalid_ohlc", "detail": ",".join(reasons)})
        if h == l == o == c:
            flat += 1

    ordered = sorted(rows, key=lambda row: row["timestamp"])
    gaps = []
    for previous, current in zip(ordered, ordered[1:]):
        delta = (current["timestamp"] - previous["timestamp"]).total_seconds()
        if delta > expected_interval_seconds:
            gaps.append({
                "from": previous["timestamp"].isoformat(),
                "to": current["timestamp"].isoformat(),
                "gap_seconds": int(delta),
                "missing_expected_bars": max(0, int(delta // expected_interval_seconds) - 1),
            })

    weekend_rows = sum(row["timestamp"].weekday() >= 5 for row in rows)
    chronological = all(
        rows[index]["timestamp"] <= rows[index + 1]["timestamp"]
        for index in range(len(rows) - 1)
    )
    unique_sorted = sorted(set(row["timestamp"] for row in rows))
    report = {
        "schema_version": 1,
        "source": {
            "file_name": path.name,
            "absolute_path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        },
        "configuration": {"expected_interval_seconds": expected_interval_seconds, "naive_timestamps_assumed_utc": True},
        "summary": {
            "parsed_rows": len(rows),
            "unique_timestamps": len(unique_sorted),
            "duplicate_timestamp_groups": len(duplicate_stamps),
            "duplicate_rows_beyond_first": sum(count - 1 for count in counts.values() if count > 1),
            "invalid_ohlc_rows": len(invalid_ohlc),
            "flat_candles": flat,
            "gap_count": len(gaps),
            "weekend_rows_utc": weekend_rows,
            "chronological_in_source": chronological,
            "naive_timestamp_rows": naive_timestamp_count,
            "parse_or_validation_issue_count": len(issues),
            "first_timestamp_utc": unique_sorted[0].isoformat(),
            "last_timestamp_utc": unique_sorted[-1].isoformat(),
        },
        "gaps": gaps,
        "duplicate_timestamps_utc": [stamp.isoformat() for stamp in duplicate_stamps],
        "invalid_ohlc": invalid_ohlc,
        "issues": issues,
        "interpretation": [
            "This is a structural data-quality audit, not proof that prices match Pocket Option.",
            "Rows are reported, never silently repaired or removed.",
            "Weekend timestamps are counted but not automatically treated as invalid.",
            "A gap is any adjacent timestamp difference greater than the configured interval.",
            "Naive timestamps are interpreted as UTC and counted for explicit review.",
        ],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a HydraAI OHLC candle CSV.")
    parser.add_argument("csv_file", type=Path, help="Path to source CSV")
    parser.add_argument("--interval-seconds", type=int, default=60, help="Expected candle interval (default: 60)")
    parser.add_argument("--report", type=Path, help="JSON report path (default: <input>.audit.json)")
    parser.add_argument("--issues-csv", type=Path, help="Optional row-level issues CSV path")
    args = parser.parse_args(argv)
    if args.interval_seconds <= 0:
        parser.error("--interval-seconds must be positive")

    try:
        report = audit_csv(args.csv_file, args.interval_seconds)
    except Exception as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        return 2

    report_path = args.report or args.csv_file.with_suffix(args.csv_file.suffix + ".audit.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.issues_csv:
        args.issues_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.issues_csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("line", "type", "detail"))
            writer.writeheader()
            writer.writerows(report["issues"])

    summary = report["summary"]
    print("HYDRAAI DATA AUDIT")
    print(f"File: {report['source']['file_name']}")
    print(f"SHA256: {report['source']['sha256']}")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"JSON report: {report_path}")
    if args.issues_csv:
        print(f"Issues CSV: {args.issues_csv}")
    return 1 if summary["invalid_ohlc_rows"] or summary["parse_or_validation_issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
