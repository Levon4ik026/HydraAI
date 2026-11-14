#!/usr/bin/env python3
"""Prospective, fail-closed validation of the three frozen Hydra candidates.

Pre-period warm-up is used only for causal indicator initialization and prior
completed UTC day/week levels. No warm-up signal or outcome is scored.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

from build_m5_feature_matrix import build_rows, safe
from reproduce_m5_bb_williams_adx import Bar, make_m5
from universal_profile_engine import build_candidate_events, read_matrix

UTC = timezone.utc
PAYOUT_GRID = (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.95, 1.00)
MIN_TRADES = 30
M5_MINUTES = 5

FROZEN = {
    "HYD-CAND-001": ("rsi_bearish_level", "PUT", 1, False, 60, 13, None),
    "HYD-CAND-008": ("previous_week_low_sweep_reclaim_bullish", "PUT", 6, True, 60, 13,
                     "previous_observed_utc_week_low"),
    "HYD-CAND-010": ("previous_day_low_close_breakout", "CALL", 12, True, 14, 12,
                     "previous_observed_utc_day_low"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc_timestamp(raw: str, column: str) -> datetime:
    value = raw.strip()
    if column == "timestamp":
        try:
            number = float(value)
            if number > 1_000_000_000_000:
                number /= 1000.0
            return datetime.fromtimestamp(number, tz=UTC)
        except ValueError:
            pass
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp.astimezone(UTC)


def gap_summary(bars: list[Bar]) -> dict:
    missing = []
    for previous, current in zip(bars, bars[1:]):
        minutes = int((current.timestamp - previous.timestamp).total_seconds() // 60)
        if minutes > 1:
            missing.append(minutes - 1)
    return {
        "gap_intervals": len(missing),
        "missing_m1_minutes": sum(missing),
        "largest_missing_interval_minutes": max(missing, default=0),
    }


def load_split_bars(source: Path, warmup_start: date, forward_start: date,
                    forward_end: date) -> tuple[list[Bar], list[Bar], dict]:
    if not (warmup_start < forward_start <= forward_end):
        raise ValueError("Expected warmup_start < forward_start <= forward_end")

    raw_rows = invalid_rows = duplicate_rows = out_of_range_rows = 0
    seen: dict[datetime, tuple[float, float, float, float]] = {}
    start_dt = datetime.combine(warmup_start, datetime.min.time(), tzinfo=UTC)
    forward_dt = datetime.combine(forward_start, datetime.min.time(), tzinfo=UTC)
    end_exclusive = datetime.combine(forward_end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        timestamp_column = next((x for x in ("timestamp", "datetime_utc", "datetime") if x in fields), None)
        if timestamp_column is None or not {"open", "high", "low", "close"}.issubset(fields):
            raise ValueError(f"Unsupported M1 CSV header: {sorted(fields)}")

        for row in reader:
            raw_rows += 1
            try:
                stamp = parse_utc_timestamp(row[timestamp_column], timestamp_column)
                values = tuple(float(row[key]) for key in ("open", "high", "low", "close"))
                if stamp.second != 0 or stamp.microsecond != 0:
                    raise ValueError("M1 timestamp is not minute-aligned")
                if not all(math.isfinite(x) and x > 0 for x in values):
                    raise ValueError("non-finite or non-positive OHLC")
                open_, high, low, close = values
                if high < max(open_, low, close) or low > min(open_, close):
                    raise ValueError("invalid OHLC ordering")
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                invalid_rows += 1
                continue

            if stamp < start_dt or stamp >= end_exclusive:
                out_of_range_rows += 1
                continue
            previous = seen.get(stamp)
            if previous is not None:
                duplicate_rows += 1
                if previous != values:
                    raise ValueError(f"Conflicting duplicate M1 timestamp: {stamp.isoformat()}")
                continue
            seen[stamp] = values

    if not seen:
        raise ValueError("No valid M1 rows in the requested warm-up/forward interval")
    all_bars = [Bar(stamp, *seen[stamp]) for stamp in sorted(seen)]
    warmup = [bar for bar in all_bars if bar.timestamp < forward_dt]
    forward = [bar for bar in all_bars if bar.timestamp >= forward_dt]
    if not warmup:
        raise ValueError("No pre-forward warm-up rows; prior UTC day/week levels cannot be initialized")
    if not forward:
        raise ValueError("No new M1 observations on or after 2026-11-10 UTC; refusing historical backfill")

    stats = {
        "raw_download_rows": raw_rows,
        "valid_unique_rows": len(all_bars),
        "invalid_rows": invalid_rows,
        "duplicate_timestamp_rows": duplicate_rows,
        "out_of_range_rows": out_of_range_rows,
        "warmup_rows": len(warmup),
        "forward_rows": len(forward),
        "warmup_first_utc": warmup[0].timestamp.isoformat(),
        "warmup_last_utc": warmup[-1].timestamp.isoformat(),
        "forward_first_utc": forward[0].timestamp.isoformat(),
        "forward_last_utc": forward[-1].timestamp.isoformat(),
        "forward_observed_days": len({bar.timestamp.date() for bar in forward}),
        "warmup_m1_gaps": gap_summary(warmup),
        "forward_m1_gaps": gap_summary(forward),
    }
    return warmup, forward, stats


def write_m1_csv(path: Path, bars: list[Bar]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("timestamp", "open", "high", "low", "close"))
        for bar in bars:
            writer.writerow((int(bar.timestamp.timestamp() * 1000),
                             repr(bar.open), repr(bar.high), repr(bar.low), repr(bar.close)))


def count_incomplete_m5_buckets(bars: list[Bar]) -> int:
    buckets: dict[datetime, list[datetime]] = defaultdict(list)
    for bar in bars:
        start = bar.timestamp.replace(minute=(bar.timestamp.minute // 5) * 5, second=0, microsecond=0)
        buckets[start].append(bar.timestamp)
    incomplete = 0
    for start, stamps in buckets.items():
        expected = [start + timedelta(minutes=offset) for offset in range(5)]
        if sorted(stamps) != expected:
            incomplete += 1
    return incomplete


def write_feature_matrix(combined_path: Path, matrix_path: Path,
                         segments: list[list[Bar]], combined_rows: int) -> dict:
    rows = iter(build_rows(segments))
    first = next(rows, None)
    if first is None:
        raise ValueError("No complete M5 bars produced from validated M1 observations")

    columns = list(first.keys())
    row_count = 0
    with matrix_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                writer = csv.DictWriter(text, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                writer.writerow({key: safe(value) for key, value in first.items()})
                row_count = 1
                for row in rows:
                    writer.writerow({key: safe(value) for key, value in row.items()})
                    row_count += 1

    expected_rows = sum(len(segment) for segment in segments)
    if row_count != expected_rows:
        raise ValueError(f"M5 matrix row mismatch: wrote={row_count}, expected={expected_rows}")
    return {
        "feature_version": "hydra_m5_causal_features_v1",
        "combined_m1_file": combined_path.name,
        "combined_m1_sha256": sha256_file(combined_path),
        "m1_valid_rows": combined_rows,
        "m5_complete_rows": expected_rows,
        "gap_separated_segments": len(segments),
        "matrix_file": matrix_path.name,
        "matrix_rows": row_count,
        "matrix_sha256": sha256_file(matrix_path),
        "causality": {
            "signal": "completed UTC-aligned M5 bar close",
            "entry": "immediately next M5 open in the same continuity segment",
            "settlement": "expiry bar close in the same continuity segment",
            "indicators": "completed bars only; reset at every missing M5 bucket",
            "previous_day_week_levels": "previous observed completed UTC calendar day/week only",
            "atr_rank": "prior 120 completed M5 bars only; current signal bar excluded",
        },
    }


def validate_candidate_config(config: dict) -> None:
    candidates = config.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise ValueError("Forward validation requires exactly three frozen candidate definitions")
    by_id = {candidate.get("id"): candidate for candidate in candidates}
    if set(by_id) != set(FROZEN):
        raise ValueError(f"Candidate IDs differ from frozen set: {sorted(by_id)}")
    for candidate_id, expected in FROZEN.items():
        candidate = by_id[candidate_id]
        actual = (
            candidate.get("event_type"), candidate.get("side"), candidate.get("expiry_bars"),
            candidate.get("nonoverlap"), candidate.get("min_signal_index"),
            candidate.get("tail_guard"), candidate.get("background_requires_level"),
        )
        if actual != expected:
            raise ValueError(f"Frozen definition drift for {candidate_id}: {actual!r} != {expected!r}")
        if candidate.get("split_settlement", "bar_close") != "bar_close":
            raise ValueError(f"Unsupported settlement convention for {candidate_id}")
    if not config.get("dataset", {}).get("snapshot_id"):
        raise ValueError("Frozen baseline config is missing its historical snapshot identity")


def pnl_for(outcome: str, payout: float) -> float:
    return payout if outcome == "W" else -1.0 if outcome == "L" else 0.0


def period_concentration(trades: list[dict], granularity: str, payout: float = 0.92) -> dict:
    groups: dict[str, float] = defaultdict(float)
    for trade in trades:
        stamp = trade["entry_time"]
        if granularity == "day":
            key = stamp.date().isoformat()
        elif granularity == "week":
            iso = stamp.isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
        else:
            raise ValueError(f"Unsupported concentration granularity: {granularity}")
        groups[key] += pnl_for(trade["outcome"], payout)
    positive = [(key, value) for key, value in groups.items() if value > 0]
    denominator = sum(value for _, value in positive)
    if not positive or denominator <= 0:
        return {"top_period": None, "top_positive_net_units": 0.0,
                "total_positive_period_net_units": round(denominator, 8), "share_pct": None}
    key, value = max(positive, key=lambda item: item[1])
    return {"top_period": key, "top_positive_net_units": round(value, 8),
            "total_positive_period_net_units": round(denominator, 8),
            "share_pct": round(100.0 * value / denominator, 4)}


def stability_rows(trades: list[dict], observed_days: set[date], granularity: str,
                   payout: float = 0.92) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)

    def key_for_day(day: date) -> str:
        if granularity == "week":
            iso = day.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        return day.strftime("%Y-%m")

    for day in observed_days:
        groups.setdefault(key_for_day(day), [])
    for trade in trades:
        groups[key_for_day(trade["entry_time"].date())].append(trade)

    output = []
    for key in sorted(groups):
        rows = groups[key]
        wins = sum(row["outcome"] == "W" for row in rows)
        losses = sum(row["outcome"] == "L" for row in rows)
        draws = sum(row["outcome"] == "D" for row in rows)
        decisive = wins + losses
        output.append({
            "period": key, "n": len(rows), "w": wins, "l": losses, "d": draws,
            "wr_pct": round(100.0 * wins / decisive, 4) if decisive else None,
            "net_units": round(wins * payout - losses, 8),
        })
    return output


def summarize_metrics(trades: list[dict], observed_days: set[date] | None = None) -> dict:
    ordered = sorted(trades, key=lambda row: (row["entry_time"], row["signal_time"]))
    wins = sum(row["outcome"] == "W" for row in ordered)
    losses = sum(row["outcome"] == "L" for row in ordered)
    draws = sum(row["outcome"] == "D" for row in ordered)
    decisive = wins + losses
    equity = peak = max_drawdown = 0.0
    streak = longest_streak = 0
    for trade in ordered:
        equity += pnl_for(trade["outcome"], 0.92)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if trade["outcome"] == "L":
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    observed_days = observed_days or set()
    active_days = len({trade["entry_time"].date() for trade in ordered})
    return {
        "n": len(ordered), "w": wins, "l": losses, "d": draws, "decisive": decisive,
        "wr_pct": round(100.0 * wins / decisive, 4) if decisive else None,
        "net_92_units": round(wins * 0.92 - losses, 8),
        "max_drawdown_92_units": round(max_drawdown, 8),
        "longest_losing_streak": longest_streak,
        "active_days": active_days, "observed_forward_days": len(observed_days),
        "trades_per_active_day": round(len(ordered) / active_days, 4) if active_days else 0.0,
        "payout_sensitivity": {f"{p:.2f}": round(wins * p - losses, 8) for p in PAYOUT_GRID},
        "daily_profit_concentration": period_concentration(ordered, "day"),
        "weekly_profit_concentration": period_concentration(ordered, "week"),
        "weekly_stability": stability_rows(ordered, observed_days, "week"),
        "monthly_stability": stability_rows(ordered, observed_days, "month"),
        "sample_status": "DESCRIPTIVE_ONLY_INSUFFICIENT_N" if len(ordered) < MIN_TRADES
                         else "MINIMUM_N_REACHED_NOT_PROOF_OF_EDGE",
    }


def evaluate_candidate(candidate: dict, feature_segments: dict, forward_start: datetime,
                       forward_end_exclusive: datetime, observed_days: set[date]) -> dict:
    accepted, _background, purged_windows, raw = build_candidate_events(
        candidate, feature_segments, forward_start, forward_start, include_raw=True
    )
    raw_forward = [row for row in raw if row["period"] == "TEST" and row["time"] >= forward_start]
    accepted_forward = [
        row for row in accepted if row["period"] == "TEST" and row["time"] >= forward_start
    ]
    trades = []
    excluded_after_cutoff = 0
    expiry_bars = int(candidate["expiry_bars"])
    for event in accepted_forward:
        bars = feature_segments[event["segment"]]
        index = event["index"]
        entry_bar = bars[index + 1]
        settlement_bar = bars[index + expiry_bars]
        settlement_time = settlement_bar["timestamp"] + timedelta(minutes=M5_MINUTES)
        if settlement_time > forward_end_exclusive:
            excluded_after_cutoff += 1
            continue
        if event["time"] < forward_start or entry_bar["timestamp"] < forward_start:
            raise ValueError("Pre-forward event escaped the forward boundary guard")
        trades.append({
            "candidate_id": candidate["id"], "side": candidate["side"],
            "expiry_minutes": expiry_bars * M5_MINUTES,
            "signal_time": event["time"],
            "signal_available_at": event["time"] + timedelta(minutes=M5_MINUTES),
            "entry_time": entry_bar["timestamp"], "settlement_time": settlement_time,
            "entry_price": entry_bar["open"], "settlement_price": settlement_bar["close"],
            "outcome": event["outcome"], "segment_id": event["segment"],
            "signal_bar_index": index,
        })
    return {
        "candidate_id": candidate["id"], "side": candidate["side"],
        "expiry_minutes": expiry_bars * M5_MINUTES,
        "raw_forward_events": len(raw_forward), "accepted_forward_events_before_cutoff_guard": len(accepted_forward),
        "overlap_suppressed_events": len(raw_forward) - len(accepted_forward),
        "boundary_purged_m5_windows": purged_windows,
        "excluded_after_forward_cutoff": excluded_after_cutoff,
        "metrics": summarize_metrics(trades, observed_days), "trades": trades,
    }


def write_trades_csv(path: Path, trades: list[dict]) -> None:
    fields = ("candidate_id", "side", "expiry_minutes", "signal_time_utc",
              "signal_available_at_utc", "entry_time_utc", "settlement_time_utc",
              "entry_price", "settlement_price", "outcome", "profit_at_92",
              "segment_id", "signal_bar_index")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for trade in sorted(trades, key=lambda row: (row["candidate_id"], row["entry_time"])):
            writer.writerow({
                "candidate_id": trade["candidate_id"], "side": trade["side"],
                "expiry_minutes": trade["expiry_minutes"],
                "signal_time_utc": trade["signal_time"].isoformat(),
                "signal_available_at_utc": trade["signal_available_at"].isoformat(),
                "entry_time_utc": trade["entry_time"].isoformat(),
                "settlement_time_utc": trade["settlement_time"].isoformat(),
                "entry_price": repr(trade["entry_price"]),
                "settlement_price": repr(trade["settlement_price"]),
                "outcome": trade["outcome"],
                "profit_at_92": repr(pnl_for(trade["outcome"], 0.92)),
                "segment_id": trade["segment_id"], "signal_bar_index": trade["signal_bar_index"],
            })


def fmt_wr(value) -> str:
    return "n/a" if value is None else f"{value:.2f}%"


def fmt_concentration(value: dict) -> str:
    if value["share_pct"] is None:
        return "n/a (no positive period net P&L)"
    return (f"{value['top_period']}: {value['share_pct']:.2f}% of "
            f"{value['total_positive_period_net_units']:+.2f}u positive period net")


def build_report(manifest: dict, results: list[dict]) -> str:
    data = manifest["data"]
    lines = [
        "# HydraAI — three-candidate prospective forward validation", "",
        f"- Captured UTC: {manifest['captured_at_utc']}",
        f"- Branch / code commit: {manifest.get('branch', 'unknown')} / {manifest.get('git_sha', 'unknown')}",
        f"- Forward cohort: {manifest['forward_start_utc']} through requested UTC date {manifest['requested_forward_end_utc']}",
        f"- Actual forward M1 range: {data['forward_first_utc']} — {data['forward_last_utc']}",
        f"- Forward M1 rows: {data['forward_rows']:,}; observed UTC dates: {data['forward_observed_days']}",
        f"- Warm-up-only M1 range: {data['warmup_first_utc']} — {data['warmup_last_utc']} ({data['warmup_rows']:,} rows)",
        f"- Raw downloaded file SHA-256: {manifest['raw_download_sha256']}",
        f"- Forward-only CSV SHA-256: {manifest['forward_csv_sha256']}",
        f"- Warm-up-only CSV SHA-256: {manifest['warmup_csv_sha256']}",
        f"- Combined feature-input SHA-256: {manifest['combined_csv_sha256']}",
        f"- M5 feature matrix SHA-256: {manifest['matrix']['matrix_sha256']}",
        f"- Frozen candidate config SHA-256: {manifest['candidate_config_sha256']}",
        f"- Preregistration protocol SHA-256: {manifest['protocol_sha256']}", "",
        "## Data integrity and causal construction", "",
        f"- Raw rows: {data['raw_download_rows']:,}; valid unique rows in requested interval: {data['valid_unique_rows']:,}.",
        f"- Invalid rows excluded: {data['invalid_rows']}; identical duplicate timestamps removed: {data['duplicate_timestamp_rows']}; out-of-range rows excluded: {data['out_of_range_rows']}.",
        f"- Forward M1 gaps: {data['forward_m1_gaps']['gap_intervals']} intervals, {data['forward_m1_gaps']['missing_m1_minutes']:,} missing minutes; largest interval {data['forward_m1_gaps']['largest_missing_interval_minutes']:,} minutes.",
        f"- Warm-up M1 gaps: {data['warmup_m1_gaps']['gap_intervals']} intervals, {data['warmup_m1_gaps']['missing_m1_minutes']:,} missing minutes.",
        f"- Complete M5 bars from warm-up + forward: {manifest['matrix']['m5_complete_rows']:,}; continuity segments: {manifest['matrix']['gap_separated_segments']:,}; incomplete UTC-aligned M5 buckets excluded: {manifest['incomplete_m5_buckets']:,}.",
        f"- Forward M5 bars: {manifest['forward_m5_bars']:,}; forward segments containing at least one forward bar: {manifest['forward_continuity_segments']:,}.",
        "- Warm-up rows initialize causal indicators and prior observed completed UTC day/week levels only. No warm-up signal or outcome is scored.",
        "- Signals use completed M5 bars; entry is the immediately next M5 open; settlement is the expiry bar close. Trades crossing the forward-start boundary, a missing M5 bucket, or a continuity-segment boundary are not accepted.",
        "", "## Candidate results", "",
        "| Candidate | Side / expiry | N | W/L/D | WR excl. draws | Net at 92% | Max DD | Longest L streak | Active days | Trades / active day |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        m = result["metrics"]
        lines.append(
            f"| {result['candidate_id']} | {result['side']} / {result['expiry_minutes']}m | {m['n']} "
            f"| {m['w']}/{m['l']}/{m['d']} | {fmt_wr(m['wr_pct'])} | {m['net_92_units']:+.2f}u "
            f"| {m['max_drawdown_92_units']:.2f}u | {m['longest_losing_streak']} | {m['active_days']} "
            f"| {m['trades_per_active_day']:.2f} |"
        )

    lines += ["", "### Profit concentration", "",
              "| Candidate | Top UTC day | Top UTC week |", "|---|---|---|"]
    for result in results:
        m = result["metrics"]
        lines.append(f"| {result['candidate_id']} | {fmt_concentration(m['daily_profit_concentration'])} "
                     f"| {fmt_concentration(m['weekly_profit_concentration'])} |")

    lines += ["", "### Payout sensitivity (net units)", "",
              "| Payout | HYD-CAND-001 | HYD-CAND-008 | HYD-CAND-010 |",
              "|---:|---:|---:|---:|"]
    by_id = {result["candidate_id"]: result for result in results}
    for payout in PAYOUT_GRID:
        values = [by_id[candidate_id]["metrics"]["payout_sensitivity"][f"{payout:.2f}"]
                  for candidate_id in FROZEN]
        lines.append(f"| {payout:.0%} | {values[0]:+.2f} | {values[1]:+.2f} | {values[2]:+.2f} |")

    for result in results:
        m = result["metrics"]
        lines += ["", f"### {result['candidate_id']} — weekly/monthly stability", "",
                  f"- Raw forward trigger events: {result['raw_forward_events']}; accepted trades: {m['n']}; "
                  f"overlap-suppressed events: {result['overlap_suppressed_events']}.",
                  f"- Boundary-crossing M5 windows purged: {result['boundary_purged_m5_windows']}; "
                  f"trades excluded after the requested data cutoff: {result['excluded_after_forward_cutoff']}.",
                  f"- Sample status: {m['sample_status']}.", "",
                  "| UTC week | N | W/L/D | WR | Net u at 92% |", "|---|---:|---|---:|---:|"]
        if m["weekly_stability"]:
            for row in m["weekly_stability"]:
                lines.append(f"| {row['period']} | {row['n']} | {row['w']}/{row['l']}/{row['d']} "
                             f"| {fmt_wr(row['wr_pct'])} | {row['net_units']:+.2f} |")
        else:
            lines.append("| — | 0 | 0/0/0 | n/a | +0.00 |")
        lines += ["", "| UTC month | N | W/L/D | WR | Net u at 92% |", "|---|---:|---|---:|---:|"]
        if m["monthly_stability"]:
            for row in m["monthly_stability"]:
                lines.append(f"| {row['period']} | {row['n']} | {row['w']}/{row['l']}/{row['d']} "
                             f"| {fmt_wr(row['wr_pct'])} | {row['net_units']:+.2f} |")
        else:
            lines.append("| — | 0 | 0/0/0 | n/a | +0.00 |")

    all_reached = all(result["metrics"]["n"] >= MIN_TRADES for result in results)
    threshold_note = ("All three have reached 30 trades; this remains observational evidence, not proof of edge."
                      if all_reached else
                      "At least one candidate is below 30 new trades; results are descriptive only.")
    lines += ["", "## Interpretation and limitations", "",
              f"- Minimum sample threshold: {MIN_TRADES} new trades per candidate. {threshold_note}",
              "- No candidate, signal, threshold, direction, expiry, or entry/settlement convention was added or changed.",
              "- Candidates are not pooled into a portfolio; overlap and capital allocation were not preregistered.",
              "- The 92% payout and sensitivity grid are accounting scenarios, not recorded platform payouts.",
              "- Dukascopy EURUSD BID candles are not Pocket Option executable quotes. Spread, quote construction, actual platform payout, latency, and platform settlement rules are not modeled. These results do not establish executable Pocket Option profitability.",
              "- This is prospective observational validation. Do not tune or gate frozen rules using these forward observations.",
              "", "## Reproducibility", "",
              f"- Workflow run ID: {manifest.get('workflow_run_id', 'local')}",
              f"- Workflow URL: {manifest.get('workflow_run_url', 'not available')}",
              "- Machine-readable manifest: manifest.json.",
              "- Trade-level outcomes: trades.csv.",
              "- Validated warm-up, forward-only, combined M1 files, and causal M5 matrix are retained in the workflow artifact.", ""]
    return "\n".join(lines)


def run_pipeline(args) -> dict:
    source = args.data.resolve()
    config_path = args.config.resolve()
    protocol_path = args.protocol.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_candidate_config(config)
    warmup, forward, data_stats = load_split_bars(
        source, args.warmup_start, args.forward_start, args.forward_end
    )
    combined = sorted(warmup + forward, key=lambda bar: bar.timestamp)

    raw_copy = out_dir / "raw-download.csv"
    raw_copy.write_bytes(source.read_bytes())
    warmup_path = out_dir / "warmup-only.csv"
    forward_path = out_dir / "forward-cohort.csv"
    combined_path = out_dir / "combined-feature-input.csv"
    matrix_path = out_dir / "causal-m5-feature-matrix.csv.gz"
    trades_path = out_dir / "trades.csv"
    manifest_path = out_dir / "manifest.json"
    report_path = out_dir / "report.md"

    write_m1_csv(warmup_path, warmup)
    write_m1_csv(forward_path, forward)
    write_m1_csv(combined_path, combined)

    segments = make_m5(combined)
    matrix_meta = write_feature_matrix(combined_path, matrix_path, segments, len(combined))
    feature_segments = read_matrix(matrix_path)

    forward_start_dt = datetime.combine(args.forward_start, datetime.min.time(), tzinfo=UTC)
    forward_end_exclusive = datetime.combine(args.forward_end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    forward_matrix_rows = [row for rows in feature_segments.values() for row in rows
                           if row["timestamp"] >= forward_start_dt]
    if not forward_matrix_rows:
        raise ValueError("No complete forward M5 bars after 2026-11-10 UTC")
    if not any(row.get("previous_observed_utc_week_low") not in (None, "") for row in forward_matrix_rows):
        raise ValueError("Warm-up does not establish a prior observed completed UTC week low")
    if not any(row.get("previous_observed_utc_day_low") not in (None, "") for row in forward_matrix_rows):
        raise ValueError("Warm-up does not establish a prior observed completed UTC day low")

    observed_days = {bar.timestamp.date() for bar in forward}
    by_id = {candidate["id"]: candidate for candidate in config["candidates"]}
    results = []
    all_trades = []
    for candidate_id in FROZEN:
        result = evaluate_candidate(by_id[candidate_id], feature_segments,
                                    forward_start_dt, forward_end_exclusive, observed_days)
        all_trades.extend(result.pop("trades"))
        results.append(result)
    write_trades_csv(trades_path, all_trades)

    forward_segment_ids = {sid for sid, rows in feature_segments.items()
                            if any(row["timestamp"] >= forward_start_dt for row in rows)}
    manifest = {
        "protocol": "three-candidate-forward-validation-protocol-v1",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "branch": os.environ.get("GITHUB_REF_NAME", "local"),
        "git_sha": os.environ.get("GITHUB_SHA", "local"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "workflow_run_url": (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', 'Levon4ik026/HydraAI')}/actions/runs/"
            f"{os.environ.get('GITHUB_RUN_ID', '')}"
            if os.environ.get("GITHUB_RUN_ID") else "not available"
        ),
        "forward_start_utc": args.forward_start.isoformat(),
        "requested_forward_end_utc": args.forward_end.isoformat(),
        "warmup_start_utc": args.warmup_start.isoformat(),
        "raw_download_file": source.name,
        "raw_download_sha256": sha256_file(source),
        "raw_download_copy_sha256": sha256_file(raw_copy),
        "warmup_csv_sha256": sha256_file(warmup_path),
        "forward_csv_sha256": sha256_file(forward_path),
        "combined_csv_sha256": sha256_file(combined_path),
        "candidate_config_sha256": sha256_file(config_path),
        "protocol_sha256": sha256_file(protocol_path),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "data": data_stats,
        "matrix": matrix_meta,
        "forward_m5_bars": len(forward_matrix_rows),
        "forward_continuity_segments": len(forward_segment_ids),
        "incomplete_m5_buckets": count_incomplete_m5_buckets(combined),
        "payout_grid": list(PAYOUT_GRID),
        "minimum_trades_per_candidate": MIN_TRADES,
        "candidate_results": results,
        "execution_caveat": (
            "Dukascopy EURUSD BID is not Pocket Option executable pricing; spread, quote construction, "
            "platform payout, latency and settlement are not modeled."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    report_path.write_text(build_report(manifest, results), encoding="utf-8")
    return manifest


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--warmup-start", type=date.fromisoformat, default=date(2026, 11, 2))
    parser.add_argument("--forward-start", type=date.fromisoformat, default=date(2026, 11, 10))
    parser.add_argument("--forward-end", type=date.fromisoformat, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = run_pipeline(args)
    print(json.dumps({
        "status": "completed_descriptive_forward_validation",
        "forward_m1_rows": manifest["data"]["forward_rows"],
        "forward_m1_first_utc": manifest["data"]["forward_first_utc"],
        "forward_m1_last_utc": manifest["data"]["forward_last_utc"],
        "candidate_trade_counts": {
            row["candidate_id"]: row["metrics"]["n"] for row in manifest["candidate_results"]
        },
        "report": str(args.out_dir / "report.md"),
        "manifest": str(args.out_dir / "manifest.json"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
