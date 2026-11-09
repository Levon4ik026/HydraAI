#!/usr/bin/env python3
"""Frozen MEAN_REV_20_Z1.5 prospective audit.

Primary CALL rule is frozen from the prior screen. Features use only the prior
20 completed M5 closes; population standard deviation; current completed candle
must be bullish and close above the previous close. Entry is next M5 open and
settlement is the close of that entry candle. Payout is fixed at 92%.
The mirrored PUT is a separate symmetry diagnostic, not a tuned replacement.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import random
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from reproduce_m5_bb_williams_adx import Bar, make_m5

PAYOUT = 0.92
WINDOW = 20
Z_THRESHOLD = 1.5
HOLDOUT_START = datetime(2026, 11, 9, tzinfo=timezone.utc)
RANDOM_REPLICATES = 10_000
RANDOM_SEED = 20261109
EPS = 1e-12
PERIODS = ("TRAIN", "VALIDATION", "PRIOR-INSPECTED TEST", "FRESH HOLDOUT")


def parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_dukascope_m1(path: Path, snapshot_utc: datetime):
    """Audit raw CSV bytes and retain only completed, valid M1 candles."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    parsed: dict[datetime, Bar] = {}
    raw_rows = invalid_rows = duplicate_rows = 0
    raw_valid_times = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "open", "high", "low", "close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Expected Dukascopy columns {sorted(required)}, got {reader.fieldnames}")
        for row in reader:
            raw_rows += 1
            try:
                ts = datetime.fromtimestamp(int(float(row["timestamp"])) / 1000.0, tz=timezone.utc)
                o, h, low, c = (float(row[k]) for k in ("open", "high", "low", "close"))
                if not all(math.isfinite(x) and x > 0 for x in (o, h, low, c)):
                    raise ValueError("non-finite or non-positive OHLC")
                if h < max(o, low, c) or low > min(o, c):
                    raise ValueError("invalid OHLC ordering")
            except (ValueError, TypeError, OverflowError):
                invalid_rows += 1
                continue
            raw_valid_times.append(ts)
            if ts in parsed:
                duplicate_rows += 1
            parsed[ts] = Bar(ts, o, h, low, c)

    all_valid = [parsed[t] for t in sorted(parsed)]
    completed = [
        bar for bar in all_valid
        if bar.timestamp + timedelta(minutes=1) <= snapshot_utc
    ]
    incomplete_rows = len(all_valid) - len(completed)

    gap_count = missing_minutes = 0
    for left, right in zip(completed, completed[1:]):
        minutes = int((right.timestamp - left.timestamp).total_seconds() // 60)
        if minutes > 1:
            gap_count += 1
            missing_minutes += minutes - 1

    segments = make_m5(completed)
    flat_m5 = [bar for segment in segments for bar in segment]
    holdout_segments = [
        segment for segment in segments
        if any(bar.timestamp >= HOLDOUT_START for bar in segment)
    ]
    metadata = {
        "sha256": digest,
        "raw_rows": raw_rows,
        "valid_unique_m1_rows": len(all_valid),
        "invalid_rows": invalid_rows,
        "duplicate_timestamp_rows": duplicate_rows,
        "incomplete_m1_rows_excluded": incomplete_rows,
        "raw_first_utc": min(raw_valid_times).isoformat() if raw_valid_times else "n/a",
        "raw_last_utc": max(raw_valid_times).isoformat() if raw_valid_times else "n/a",
        "completed_first_utc": completed[0].timestamp.isoformat() if completed else "n/a",
        "completed_last_utc": completed[-1].timestamp.isoformat() if completed else "n/a",
        "m1_gap_count": gap_count,
        "m1_missing_minutes": missing_minutes,
        "complete_m5_bars": len(flat_m5),
        "m5_segments": len(segments),
        "first_m5_utc": flat_m5[0].timestamp.isoformat() if flat_m5 else "n/a",
        "last_m5_utc": flat_m5[-1].timestamp.isoformat() if flat_m5 else "n/a",
        "holdout_m5_bars": sum(1 for b in flat_m5 if b.timestamp >= HOLDOUT_START),
        "holdout_segments": len(holdout_segments),
        "holdout_segment_ranges": [
            (segment[0].timestamp.isoformat(), segment[-1].timestamp.isoformat(), len(segment))
            for segment in holdout_segments
        ],
    }
    return completed, segments, metadata


def prior_close_zscore(bars: list[Bar], signal_index: int) -> float | None:
    """Z-score of close[i-1] against closes[i-20:i], population std."""
    if signal_index < WINDOW:
        return None
    values = [bars[j].close for j in range(signal_index - WINDOW, signal_index)]
    mu = sum(values) / WINDOW
    variance = sum((x - mu) ** 2 for x in values) / WINDOW
    sd = math.sqrt(variance)
    if sd <= EPS:
        return None
    return (bars[signal_index - 1].close - mu) / sd


def classify_period(signal_time: datetime, settle_time: datetime,
                    d1, d2, snapshot_utc: datetime) -> str | None:
    """Purge trades crossing any chronological boundary."""
    if signal_time >= HOLDOUT_START:
        return "FRESH HOLDOUT" if settle_time <= snapshot_utc else None
    if settle_time >= HOLDOUT_START:
        return None
    signal_day = signal_time.date()
    settle_day = settle_time.date()
    if signal_day < d1:
        return "TRAIN" if settle_day < d1 else None
    if signal_day < d2:
        return "VALIDATION" if settle_day < d2 else None
    return "PRIOR-INSPECTED TEST"


def chronological_boundaries(segments):
    days = sorted({
        bar.timestamp.date()
        for segment in segments
        for bar in segment
        if bar.timestamp < HOLDOUT_START
    })
    if len(days) < 30:
        raise ValueError(f"Need at least 30 pre-holdout M5 dates, found {len(days)}")
    return days[int(0.60 * len(days))], days[int(0.80 * len(days))]


def event_stream(segments, side: str, regime_only: bool = False):
    """Generate candidate or same-z-regime events using completed bars only."""
    events = []
    for segment_id, bars in enumerate(segments):
        for i in range(WINDOW, len(bars) - 1):
            z = prior_close_zscore(bars, i)
            if z is None:
                continue
            current = bars[i]
            previous = bars[i - 1]
            if side == "CALL":
                in_regime = z <= -Z_THRESHOLD
                confirmed = current.close > current.open and current.close > previous.close
            else:
                in_regime = z >= Z_THRESHOLD
                confirmed = current.close < current.open and current.close < previous.close
            if in_regime and (regime_only or confirmed):
                entry = bars[i + 1]
                events.append({
                    "segment": segment_id,
                    "index": i,
                    "signal_time": current.timestamp,
                    "entry_time": entry.timestamp,
                    "settle_time": entry.timestamp + timedelta(minutes=5),
                    "delta": entry.close - entry.open,
                    "z": z,
                })
    return events


def eligible_slots(segments, d1, d2, snapshot_utc):
    """Executable signal slots after warm-up and split-boundary purges."""
    counts = {period: 0 for period in PERIODS}
    for segment in segments:
        for i in range(WINDOW, len(segment) - 1):
            signal_time = segment[i].timestamp
            settle_time = segment[i + 1].timestamp + timedelta(minutes=5)
            period = classify_period(signal_time, settle_time, d1, d2, snapshot_utc)
            if period:
                counts[period] += 1
    return counts


def events_by_period(events, d1, d2, snapshot_utc):
    result = {period: [] for period in PERIODS}
    purged = 0
    for event in events:
        period = classify_period(event["signal_time"], event["settle_time"],
                                 d1, d2, snapshot_utc)
        if period:
            result[period].append(event)
        else:
            purged += 1
    for period in PERIODS:
        result[period].sort(key=lambda e: (e["signal_time"], e["segment"], e["index"]))
    return result, purged


def nonoverlap(events):
    """One active trade per rule; a signal after the prior close is allowed."""
    next_index = defaultdict(lambda: -1)
    accepted = []
    for event in events:
        sid, index = event["segment"], event["index"]
        if index >= next_index[sid]:
            accepted.append(event)
            next_index[sid] = index + 1
    return accepted


def outcome(delta: float, side: str) -> str:
    if abs(delta) <= EPS:
        return "D"
    return "W" if ((delta > 0) == (side == "CALL")) else "L"


def wilson(wins: int, decisive: int):
    if decisive <= 0:
        return None
    z = 1.959963984540054
    p = wins / decisive
    den = 1.0 + z * z / decisive
    center = (p + z * z / (2.0 * decisive)) / den
    half = z * math.sqrt(p * (1.0 - p) / decisive + z * z / (4.0 * decisive * decisive)) / den
    return 100.0 * (center - half), 100.0 * (center + half)


def summarize(events, side: str, raw_count: int, slots: int):
    outcomes = [outcome(event["delta"], side) for event in events]
    wins, losses, draws = outcomes.count("W"), outcomes.count("L"), outcomes.count("D")
    n = len(outcomes)
    decisive = wins + losses
    net = wins * PAYOUT - losses
    gross_win = wins * PAYOUT
    pf = gross_win / losses if losses else (float("inf") if gross_win else 0.0)
    equity = peak = max_dd = 0.0
    streak = max_streak = 0
    for result in outcomes:
        if result == "W":
            equity += PAYOUT
            streak = 0
        elif result == "L":
            equity -= 1.0
            streak += 1
            max_streak = max(max_streak, streak)
        peak = max(peak, equity - 0.0)
        max_dd = max(max_dd, peak - equity)
    ci = wilson(wins, decisive)
    freq = 100.0 * n / slots if slots else 0.0
    return {
        "n": n, "w": wins, "l": losses, "d": draws,
        "wr": 100.0 * wins / decisive if decisive else None,
        "wilson": ci,
        "win_all": 100.0 * wins / n if n else None,
        "net": net, "roi": 100.0 * net / n if n else None,
        "pf": pf, "max_dd": max_dd, "max_streak": max_streak,
        "raw": raw_count, "frequency": freq, "wait": 100.0 - freq,
    }


def random_direction_baseline(events, candidate_net: float, seed: int):
    """50/50 random CALL/PUT assignments on the exact candidate timestamps."""
    decisive = sum(abs(event["delta"]) > EPS for event in events)
    draws = len(events) - decisive
    if not events:
        return {"n": 0, "draws": 0, "mean_net": 0.0, "median_net": 0.0,
                "lo": 0.0, "hi": 0.0, "p_ge_candidate": 0.0}
    rng = random.Random(seed)
    nets = []
    for _ in range(RANDOM_REPLICATES):
        wins = sum(rng.getrandbits(1) for _ in range(decisive))
        losses = decisive - wins
        nets.append(wins * PAYOUT - losses)
    nets.sort()
    lo = nets[int(0.025 * (len(nets) - 1))]
    hi = nets[int(0.975 * (len(nets) - 1))]
    ge = sum(value >= candidate_net for value in nets) / len(nets) * 100.0
    return {
        "n": len(events), "draws": draws,
        "mean_net": sum(nets) / len(nets),
        "median_net": nets[len(nets) // 2],
        "lo": lo, "hi": hi, "p_ge_candidate": ge,
    }


def fmt_pct(value):
    return "n/a" if value is None else f"{value:.2f}%"


def fmt_ci(value):
    return "n/a" if value is None else f"[{value[0]:.2f}, {value[1]:.2f}]%"


def fmt_num(value):
    return "inf" if value == float("inf") else f"{value:.2f}"


def build_report(path: Path, snapshot_utc: datetime, out: Path):
    _m1, segments, meta = load_dukascope_m1(path, snapshot_utc)
    d1, d2 = chronological_boundaries(segments)
    slots = eligible_slots(segments, d1, d2, snapshot_utc)

    lines = [
        "# Frozen MEAN_REV_20_Z1.5 forward holdout audit", "",
        "## Frozen rule and execution",
        "- Primary candidate: MEAN_REV_20_Z1.5_CALL; parameters are unchanged.",
        "- Prior 20 completed M5 closes only; z-score uses the immediately previous close, rolling mean, and population standard deviation.",
        "- CALL signal after the current completed M5 candle closes when z <= -1.5, current candle is bullish, and current close > previous close.",
        "- Entry at the next M5 open; settlement at the close of that entry candle (5 minutes after entry).",
        "- Mirror PUT (z >= +1.5, bearish current candle, current close < previous close) is reported separately as a symmetry diagnostic, not as a tuned replacement.",
        "- One active trade per rule, no overlap; M5 continuity segments prevent crossing data gaps; split-boundary crossings are purged.",
        "- Fixed payout: WIN +0.92u, LOSS -1u, DRAW 0u. No look-ahead; all signal features are known by the signal candle close.",
        "",
        "## Source and exact data audit",
        f"- Source: Dukascopy EURUSD M1 BID CSV, file {path.name}.",
        f"- SHA-256: {meta['sha256']}.",
        f"- Snapshot cutoff UTC: {snapshot_utc.isoformat()}; only M1 candles whose one-minute close time is <= snapshot were retained.",
        f"- Raw CSV rows: {meta['raw_rows']:,}; valid unique M1 rows: {meta['valid_unique_m1_rows']:,}; invalid rows: {meta['invalid_rows']:,}; duplicate timestamp rows: {meta['duplicate_timestamp_rows']:,}; incomplete M1 rows excluded: {meta['incomplete_m1_rows_excluded']:,}.",
        f"- Raw valid timestamp coverage: {meta['raw_first_utc']} to {meta['raw_last_utc']}.",
        f"- Completed M1 coverage used: {meta['completed_first_utc']} to {meta['completed_last_utc']}.",
        f"- M1 timestamp gaps: {meta['m1_gap_count']:,}; missing M1 minutes across those gaps: {meta['m1_missing_minutes']:,}.",
        f"- Complete UTC-aligned M5 bars: {meta['complete_m5_bars']:,}; continuity segments: {meta['m5_segments']:,}; first/last M5: {meta['first_m5_utc']} to {meta['last_m5_utc']}.",
        f"- Fresh holdout begins {HOLDOUT_START.isoformat()}; complete holdout M5 bars: {meta['holdout_m5_bars']:,}; holdout continuity segments: {meta['holdout_segments']:,}.",
    ]
    if meta["holdout_segment_ranges"]:
        lines.append("- Holdout segment ranges (start, last bar open, bars):")
        for start, end, count in meta["holdout_segment_ranges"]:
            lines.append(f"  - {start} to {end} — {count:,} M5 bars")
    lines += [
        "",
        "## Chronological periods",
        f"- TRAIN: signal dates before {d1}.",
        f"- VALIDATION: {d1} through the day before {d2}.",
        f"- PRIOR-INSPECTED TEST: {d2} through the day before {HOLDOUT_START.date()}; not an untouched holdout.",
        f"- FRESH HOLDOUT: from {HOLDOUT_START.isoformat()} onward, only trades fully settled by the snapshot cutoff.",
        "- Historical TRAIN/VALIDATION/TEST data have already been screened, including this candidate. Only the FRESH HOLDOUT period is new to this candidate audit.",
        "",
        "## Results — candidate, same-regime and matched directional controls",
        "Trade frequency = accepted non-overlapping trades / eligible M5 signal slots after warm-up and boundary purges. WAIT is its complement.",
        "",
        "| Side | Cohort | Split | n | W/L/D | Decisive WR [95% Wilson] | Wins/all | Net u | ROI | PF | Max DD u | Max loss streak | Raw signals | Frequency | WAIT |",
        "|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for side in ("CALL", "PUT"):
        candidate_raw = event_stream(segments, side, regime_only=False)
        regime_raw = event_stream(segments, side, regime_only=True)
        candidate_periods, _candidate_purged = events_by_period(candidate_raw, d1, d2, snapshot_utc)
        regime_periods, _regime_purged = events_by_period(regime_raw, d1, d2, snapshot_utc)
        for period in PERIODS:
            raw_candidate = candidate_periods[period]
            candidate_events = nonoverlap(raw_candidate)
            candidate_stats = summarize(candidate_events, side, len(raw_candidate), slots[period])
            lines.append(
                f"| {side} | Frozen candidate | {period} | {candidate_stats['n']} | "
                f"{candidate_stats['w']}/{candidate_stats['l']}/{candidate_stats['d']} | "
                f"{fmt_pct(candidate_stats['wr'])} {fmt_ci(candidate_stats['wilson'])} | "
                f"{fmt_pct(candidate_stats['win_all'])} | {candidate_stats['net']:+.2f} | "
                f"{fmt_pct(candidate_stats['roi'])} | {fmt_num(candidate_stats['pf'])} | "
                f"{candidate_stats['max_dd']:.2f} | {candidate_stats['max_streak']} | "
                f"{candidate_stats['raw']} | {candidate_stats['frequency']:.3f}% | "
                f"{candidate_stats['wait']:.3f}% |"
            )

            raw_regime = regime_periods[period]
            regime_events = nonoverlap(raw_regime)
            regime_stats = summarize(regime_events, side, len(raw_regime), slots[period])
            lines.append(
                f"| {side} | Same-z-regime baseline (no candle confirmation) | {period} | "
                f"{regime_stats['n']} | {regime_stats['w']}/{regime_stats['l']}/{regime_stats['d']} | "
                f"{fmt_pct(regime_stats['wr'])} {fmt_ci(regime_stats['wilson'])} | "
                f"{fmt_pct(regime_stats['win_all'])} | {regime_stats['net']:+.2f} | "
                f"{fmt_pct(regime_stats['roi'])} | {fmt_num(regime_stats['pf'])} | "
                f"{regime_stats['max_dd']:.2f} | {regime_stats['max_streak']} | "
                f"{regime_stats['raw']} | {regime_stats['frequency']:.3f}% | "
                f"{regime_stats['wait']:.3f}% |"
            )

            opposite = "PUT" if side == "CALL" else "CALL"
            opposite_stats = summarize(candidate_events, opposite, len(raw_candidate), slots[period])
            lines.append(
                f"| {side} | Matched opposite direction ({opposite} on identical timestamps) | {period} | "
                f"{opposite_stats['n']} | {opposite_stats['w']}/{opposite_stats['l']}/{opposite_stats['d']} | "
                f"{fmt_pct(opposite_stats['wr'])} {fmt_ci(opposite_stats['wilson'])} | "
                f"{fmt_pct(opposite_stats['win_all'])} | {opposite_stats['net']:+.2f} | "
                f"{fmt_pct(opposite_stats['roi'])} | {fmt_num(opposite_stats['pf'])} | "
                f"{opposite_stats['max_dd']:.2f} | {opposite_stats['max_streak']} | "
                f"{len(raw_candidate)} | {opposite_stats['frequency']:.3f}% | "
                f"{opposite_stats['wait']:.3f}% |"
            )

            random_stats = random_direction_baseline(
                candidate_events, candidate_stats["net"],
                RANDOM_SEED + (0 if side == "CALL" else 1) + PERIODS.index(period) * 17
            )
            lines.append(
                f"| {side} | 50/50 random direction on candidate timestamps | {period} | "
                f"{random_stats['n']} | n/a | n/a | n/a | "
                f"median {random_stats['median_net']:+.2f} "
                f"[{random_stats['lo']:+.2f}, {random_stats['hi']:+.2f}] | n/a | n/a | "
                f"n/a | n/a | {len(raw_candidate)} | "
                f"{candidate_stats['frequency']:.3f}% | {candidate_stats['wait']:.3f}% |"
            )
            lines.append(
                f"| {side} | Random P(net >= candidate) | {period} | "
                f"{random_stats['n']} | n/a | n/a | n/a | "
                f"{random_stats['p_ge_candidate']:.1f}% | n/a | n/a | n/a | n/a | "
                f"{len(raw_candidate)} | n/a | n/a |"
            )

    fresh_bars = meta["holdout_m5_bars"]
    fresh_trades = 0
    for side in ("CALL", "PUT"):
        grouped, _ = events_by_period(event_stream(segments, side), d1, d2, snapshot_utc)
        fresh_trades += len(nonoverlap(grouped["FRESH HOLDOUT"]))
    if fresh_bars == 0:
        holdout_status = "NOT RUN — no complete M5 bars were available after the frozen holdout start."
    elif fresh_trades == 0:
        holdout_status = "No candidate trades settled in the fresh window yet; the independent holdout backtest has not produced trade metrics."
    else:
        holdout_status = (
            f"Preliminary fresh forward sample only: {fresh_bars:,} complete M5 bars and "
            f"{fresh_trades:,} accepted candidate trades across CALL and mirror PUT. "
            "This is not a confirmatory sample; wait for more independent trading days."
        )

    lines += [
        "",
        "## Holdout status",
        holdout_status,
        "",
        "## Interpretation and limitations",
        "- The candidate was selected from a broad screen of 20 direction-specific families × 6 expiries (120 variants); multiple-comparison and selection bias remain.",
        "- The original short sample's positive CALL result was contradicted by the broader multi-year screen: the long-history CALL 5m result was negative in TRAIN, VALIDATION and the already-inspected TEST. The fresh window must be judged separately.",
        "- Same-z-regime baseline removes the current-candle confirmation but keeps the same extreme prior-close regime and identical entry/settlement mechanics.",
        "- Matched opposite-direction and random-direction controls use the exact candidate timestamps, entry opens and settlement closes.",
        "- Wilson intervals are descriptive and assume independent decisive trades; serial dependence, volatility clustering and repeated market regimes can make them too narrow. The fresh sample is especially small until many days accrue.",
        "- Dukascopy BID is not Pocket Option's executable quote stream. Spread, platform quote differences, variable payout, latency and execution are not modeled.",
        "- No parameter was tuned on the fresh holdout. No live integration, automatic trading or orders are used.",
        "",
        f"Random-direction Monte Carlo: {RANDOM_REPLICATES:,} replicates per side/split; seed base {RANDOM_SEED}.",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"Wrote {out}; SHA256={meta['sha256']}; M1={meta['valid_unique_m1_rows']}; "
        f"M5={meta['complete_m5_bars']}; segments={meta['m5_segments']}; "
        f"fresh_M5={fresh_bars}; fresh_candidate_trades={fresh_trades}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--snapshot-utc", required=True,
                        help="UTC snapshot taken after download; incomplete latest M1 candles are excluded")
    parser.add_argument("--out", type=Path,
                        default=Path("research/MEAN_REV_20_Z1.5_CALL_FORWARD_HOLDOUT.md"))
    args = parser.parse_args()
    snapshot = parse_utc(args.snapshot_utc)
    if snapshot < HOLDOUT_START:
        raise SystemExit("Snapshot predates the frozen holdout start")
    build_report(args.data, snapshot, args.out)


if __name__ == "__main__":
    main()
