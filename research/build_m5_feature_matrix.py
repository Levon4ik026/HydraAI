#!/usr/bin/env python3
"""Build one immutable, causal EURUSD M5 feature matrix for Hydra research.

All indicators are computed at the close of each completed M5 bar. Rolling
volatility rank uses only the preceding 120 completed bars (current excluded).
Previous-day/week levels use fully completed UTC calendar periods only.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

from reproduce_m5_bb_williams_adx import Bar, make_m5, indicators

FEATURE_VERSION = "hydra_m5_causal_features_v1"
PAYOUT_SCENARIO = 0.92


def read_m1(path: Path) -> list[Bar]:
    parsed: dict[datetime, Bar] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        tc = next((x for x in ("timestamp", "datetime_utc", "datetime") if x in fields), None)
        if tc is None or not {"open", "high", "low", "close"}.issubset(fields):
            raise ValueError(f"Unsupported M1 CSV header: {fields}")
        for row in reader:
            raw = row[tc].strip()
            ts = (datetime.fromtimestamp(int(float(raw)) / 1000, tz=timezone.utc)
                  if tc == "timestamp" else datetime.fromisoformat(raw.replace("Z", "+00:00")))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts = ts.astimezone(timezone.utc)
            o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                continue
            if h < max(o, l, c) or l > min(o, c):
                continue
            parsed[ts] = Bar(ts, o, h, l, c)
    return [parsed[t] for t in sorted(parsed)]


def ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    state = sum(values[:period]) / period
    out[period - 1] = state
    alpha = 2.0 / (period + 1)
    for i in range(period, len(values)):
        state = alpha * values[i] + (1.0 - alpha) * state
        out[i] = state
    return out


def rsi_wilder(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, len(values))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = ((period - 1) * avg_gain + gains[i - 1]) / period
        avg_loss = ((period - 1) * avg_loss + losses[i - 1]) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def safe(value):
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def period_levels(segments: list[list[Bar]], period_fn):
    grouped: dict[object, dict[str, float]] = {}
    for seg in segments:
        for b in seg:
            key = period_fn(b.timestamp)
            box = grouped.setdefault(key, {"high": -math.inf, "low": math.inf})
            box["high"] = max(box["high"], b.high)
            box["low"] = min(box["low"], b.low)
    keys = sorted(grouped)
    prior = {}
    for i, key in enumerate(keys):
        if i:
            prior[key] = grouped[keys[i - 1]]
    return grouped, prior


def day_key(ts: datetime):
    return ts.date()


def week_key(ts: datetime):
    iso = ts.isocalendar()
    return (iso.year, iso.week)


def build_rows(segments: list[list[Bar]]) -> Iterable[dict]:
    day_groups, prior_days = period_levels(segments, day_key)
    week_groups, prior_weeks = period_levels(segments, week_key)
    for segment_id, bars in enumerate(segments):
        closes = [b.close for b in bars]
        e20, e50 = ema(closes, 20), ema(closes, 50)
        rsi = rsi_wilder(closes, 14)
        ind = indicators(bars)
        tr = []
        atr: list[float | None] = [None] * len(bars)
        state = None
        for i, b in enumerate(bars):
            value = (b.high - b.low if i == 0 else
                     max(b.high - b.low, abs(b.high - bars[i - 1].close),
                         abs(b.low - bars[i - 1].close)))
            tr.append(value)
            if i == 13:
                state = sum(tr[:14]) / 14.0
            elif i > 13:
                state = (state * 13.0 + value) / 14.0
            if i >= 13:
                atr[i] = state
        for i, b in enumerate(bars):
            a = atr[i]
            rng = b.high - b.low
            history = [
                atr[j] / bars[j].close
                for j in range(max(0, i - 120), i)
                if atr[j] is not None and bars[j].close > 0
            ]
            rank = (sum(x <= a / b.close for x in history) / len(history)
                    if a is not None and b.close > 0 and len(history) >= 60 else None)
            def ret(k):
                return ((b.close - bars[i-k].close) / a
                        if i >= k and a is not None and a > 0 else None)
            e_gap = ((e20[i] - e50[i]) / a
                     if a and e20[i] is not None and e50[i] is not None else None)
            bias = (("UP" if e20[i] > e50[i] else "DOWN" if e20[i] < e50[i] else "FLAT")
                    if e20[i] is not None and e50[i] is not None else "")
            adx = ind[i]["adx"]
            adx_band = ("LOW_LT20" if adx < 20 else "MID_20_30" if adx < 30 else "HIGH_GE30") if adx is not None else ""
            vol_band = ("LOW_LE33" if rank <= 1/3 else "MID_33_67" if rank <= 2/3 else "HIGH_GT67") if rank is not None else ""
            mom6 = ret(6)
            mom_band = ("DOWN_LT_MINUS1" if mom6 < -1 else "FLAT_MINUS1_TO_1" if mom6 <= 1 else "UP_GT1") if mom6 is not None else ""
            dk, wk = day_key(b.timestamp), week_key(b.timestamp)
            pd, pw = prior_days.get(dk), prior_weeks.get(wk)
            yield {
                "segment_id": segment_id, "bar_index": i,
                "timestamp_utc": b.timestamp.isoformat(),
                "open": b.open, "high": b.high, "low": b.low, "close": b.close,
                "ema20": e20[i], "ema50": e50[i], "ema20_50_bias": bias,
                "ema20_50_gap_atr": e_gap, "rsi14": rsi[i], "adx14": adx,
                "plus_di14": ind[i]["plus_di"], "minus_di14": ind[i]["minus_di"],
                "atr14": a, "atr14_pct_close": a / b.close if a is not None else None,
                "atr_pct_rank_prior120": rank, "atr_vol_band": vol_band,
                "adx_band": adx_band, "return1_atr": ret(1), "return3_atr": ret(3),
                "return6_atr": mom6, "return12_atr": ret(12), "momentum6_band": mom_band,
                "body_range": abs(b.close - b.open) / rng if rng else None,
                "upper_wick_range": (b.high - max(b.open, b.close)) / rng if rng else None,
                "lower_wick_range": (min(b.open, b.close) - b.low) / rng if rng else None,
                "range_atr": rng / a if a else None,
                "close_location": (b.close - b.low) / rng if rng else None,
                "previous_observed_utc_day_high": pd["high"] if pd else None,
                "previous_observed_utc_day_low": pd["low"] if pd else None,
                "previous_observed_utc_week_high": pw["high"] if pw else None,
                "previous_observed_utc_week_low": pw["low"] if pw else None,
            }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="gzip CSV output")
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    m1 = read_m1(args.data)
    segments = make_m5(m1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows_iter = iter(build_rows(segments))
    first = next(rows_iter, None)
    if first is None:
        raise SystemExit("No complete M5 bars produced")
    columns = list(first.keys())
    row_count = 0
    with args.out.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            import io
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                writer = csv.DictWriter(text, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                writer.writerow({k: safe(v) for k, v in first.items()})
                row_count = 1
                for row in rows_iter:
                    writer.writerow({k: safe(v) for k, v in row.items()})
                    row_count += 1
    # Correct row count from actual matrix cardinality; fail if generator changed.
    expected = sum(len(s) for s in segments)
    if row_count != expected:
        raise SystemExit(f"Matrix row mismatch: wrote={row_count}, expected={expected}")
    manifest = {
        "feature_version": FEATURE_VERSION,
        "source_file": args.data.name,
        "source_sha256": sha256(args.data),
        "m1_valid_rows": len(m1),
        "m5_complete_rows": expected,
        "gap_separated_segments": len(segments),
        "matrix_file": args.out.name,
        "matrix_sha256": sha256(args.out),
        "matrix_rows": row_count,
        "causality": {
            "timestamp": "completed M5 bar close; entry is next M5 open",
            "atr_percentile": "prior 120 completed M5 bars only; current bar excluded; minimum 60 observations",
            "previous_day_week_levels": "previous observed completed UTC calendar period only",
            "indicators": "computed from completed bars in the same continuous segment",
        },
        "payout_scenario_only": PAYOUT_SCENARIO,
        "not_platform_execution_data": True,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in (
        "feature_version", "m1_valid_rows", "m5_complete_rows",
        "gap_separated_segments", "matrix_rows", "matrix_sha256"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
