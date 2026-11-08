#!/usr/bin/env python3
"""Single-position, non-overlapping audit with simple M5 momentum baselines.

All signals are formed at a completed M5 close, entry is the next M5 open,
and settlement is the close of the selected expiry candle. One shared position
is allowed at a time; a signal on the previous trade's expiry close is allowed.
"""
from __future__ import annotations

import argparse
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from long_history_validation import (
    PAYOUT, chronological_period, make_events, m5_close_time, read_duka,
)
from reproduce_m5_bb_williams_adx import make_m5
from long_history_validation import Bar


def make_momentum_events(segments, fade=False):
    """MOM3 baseline: follow (or fade) the last three completed M5 closes."""
    events = []
    for seg_id, bars in enumerate(segments):
        for i in range(3, len(bars) - 5):
            move = bars[i].close - bars[i - 3].close
            if abs(move) <= 1e-12:
                continue
            direction = "CALL" if move > 0 else "PUT"
            if fade:
                direction = "PUT" if direction == "CALL" else "CALL"
            events.append({
                "signal_time": bars[i].timestamp,
                "segment": seg_id,
                "bar_index": i,
                "direction": direction,
            })
    return events


def schedule_non_overlapping(events, horizon_bars):
    """One position across CALL and PUT; allow a signal on expiry-close candle."""
    if horizon_bars < 1:
        raise ValueError("horizon_bars must be positive")
    next_available = {}
    accepted = []
    for event in sorted(events, key=lambda x: (x["segment"], x["bar_index"])):
        segment = event["segment"]
        index = event["bar_index"]
        if index < next_available.get(segment, -1):
            continue
        accepted.append(event)
        next_available[segment] = index + horizon_bars
    return accepted


def score_events(events, segments, horizon_bars):
    """Score at next M5 open through the horizon candle close."""
    rows = []
    for event in events:
        bars = segments[event["segment"]]
        i = event["bar_index"]
        if i + horizon_bars >= len(bars):
            continue
        entry = bars[i + 1]
        exit_bar = bars[i + horizon_bars]
        delta = exit_bar.close - entry.open
        if abs(delta) <= 1e-12:
            outcome = "DRAW"
        elif (event["direction"] == "CALL" and delta > 0) or (
            event["direction"] == "PUT" and delta < 0
        ):
            outcome = "WIN"
        else:
            outcome = "LOSS"
        rows.append({
            **event,
            "entry_time": entry.timestamp,
            "settle_time": m5_close_time(exit_bar.timestamp),
            "outcome": outcome,
        })
    return rows


def split_name(timestamp, d1, d2):
    day = timestamp.date()
    if day < d1:
        return "TRAIN"
    if day < d2:
        return "VALIDATION"
    return "TEST"


def wilson(wins, decisive):
    if decisive <= 0:
        return None
    z = 1.959963984540054
    p = wins / decisive
    den = 1.0 + z * z / decisive
    center = (p + z * z / (2.0 * decisive)) / den
    radius = z * math.sqrt(
        p * (1.0 - p) / decisive + z * z / (4.0 * decisive * decisive)
    ) / den
    return (100.0 * (center - radius), 100.0 * (center + radius))


def metrics(rows, bar_count):
    rows = sorted(rows, key=lambda x: x["signal_time"])
    wins = sum(x["outcome"] == "WIN" for x in rows)
    losses = sum(x["outcome"] == "LOSS" for x in rows)
    draws = sum(x["outcome"] == "DRAW" for x in rows)
    decisive = wins + losses
    n = len(rows)
    net = wins * PAYOUT - losses
    gross_loss = float(losses)
    pf = wins * PAYOUT / gross_loss if gross_loss else (math.inf if wins else 0.0)
    equity = peak = max_dd = 0.0
    streak = max_streak = 0
    for row in rows:
        equity += PAYOUT if row["outcome"] == "WIN" else -1.0 if row["outcome"] == "LOSS" else 0.0
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        streak = streak + 1 if row["outcome"] == "LOSS" else 0
        max_streak = max(max_streak, streak)
    ci = wilson(wins, decisive)
    return {
        "n": n, "wins": wins, "losses": losses, "draws": draws,
        "wr": 100.0 * wins / decisive if decisive else None,
        "ci": ci, "wins_all": 100.0 * wins / n if n else None,
        "net": net, "roi": 100.0 * net / n if n else None,
        "pf": pf, "dd": max_dd, "streak": max_streak,
        "frequency": 100.0 * n / bar_count if bar_count else 0.0,
        "wait": 100.0 - (100.0 * n / bar_count if bar_count else 0.0),
    }


def fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/NONOVERLAP_BASELINE_AUDIT.md"))
    ap.add_argument("--adx-min", type=float, default=15)
    args = ap.parse_args()

    m1 = read_duka(args.data)
    segments = make_m5(m1)
    total_m5 = sum(map(len, segments))
    trigger_events = make_events(segments, args.adx_min)
    days = sorted({x["signal_time"].date() for x in trigger_events})
    if len(days) < 30:
        raise SystemExit("Insufficient signal days for chronological split.")
    d1, d2 = days[int(len(days) * 0.60)], days[int(len(days) * 0.80)]

    strategies = {
        "BB_WR_ADX": trigger_events,
        "MOM3_CONT": make_momentum_events(segments, fade=False),
        "MOM3_FADE": make_momentum_events(segments, fade=True),
    }

    bar_counts = Counter()
    for bars in segments:
        for bar in bars:
            bar_counts[split_name(bar.timestamp, d1, d2)] += 1
    bar_counts["ALL"] = total_m5

    raw_frequency = 100.0 * len(trigger_events) / max(1, total_m5)
    lines = [
        "# HYDRA — non-overlapping strategy and simple-baseline audit", "",
        f"Source: Dukascopy EURUSD M1 BID; raw M1 rows={len(m1):,}; complete UTC M5 bars={total_m5:,}; continuous segments={len(segments)}.",
        f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
        f"Frozen BB/Williams/ADX triggers={len(trigger_events):,}; raw frequency={raw_frequency:.3f}% of complete M5 bars; raw WAIT={100.0-raw_frequency:.3f}%.",
        f"Frozen strategy: BB(20,2) re-entry + Williams %R(14) cross + ADX(14)>={args.adx_min:g}.",
        "Baselines: MOM3_CONT follows the sign of close[i]-close[i-3]; MOM3_FADE takes the opposite side. Both use only the signal M5 close and prior completed candles; flat 3-bar moves are WAIT.",
        "Execution: signal after closed M5 candle i; entry at candle i+1 open; settlement at candle i+h close for h=1..5 (5..25 minutes). Fixed payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u.",
        "Scheduling: one shared position across CALL/PUT per strategy; signals during an active trade are suppressed; a signal on the expiry candle close is eligible for entry on the next candle. Each continuous segment has its own scheduler.",
        f"Chronological signal-day boundaries: TRAIN before {d1}; VALIDATION {d1} through {d2-timedelta(days=1)}; TEST from {d2}. Trades settling at or beyond the next split boundary are purged from TRAIN/VALIDATION.",
        "The historical TEST has been inspected in earlier research and is not an untouched independent holdout. Dukascopy BID is not Pocket Option's exact quote stream; spread, payout variation and platform execution are not modeled.", "",
        "## Results: one-position non-overlapping schedule", "",
        "ALL rows show total accepted frequency and the true WAIT complement. CALL/PUT rows show side-specific frequency; WAIT is shown only on ALL rows. Candidate signals rejected by overlap and trades purged at split boundaries are shown separately.",
        "| Expiry | Strategy | Split | Side | Candidates | Overlap rejected | Boundary purged | Scored n | W/L/D | Decisive WR | Wilson 95% CI | Wins/all | Net u | ROI | PF | Max DD u | Max loss streak | Side/total frequency | Global WAIT |",
        "|---:|---|---|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for horizon in (1, 2, 3, 4, 5):
        for strategy_name, candidates in strategies.items():
            scheduled = schedule_non_overlapping(candidates, horizon)
            scored = score_events(scheduled, segments, horizon)
            split_rows = {"ALL": scored, "TRAIN": [], "VALIDATION": [], "TEST": []}
            purged_rows = {"TRAIN": [], "VALIDATION": []}
            for row in scored:
                period = chronological_period(row["signal_time"], row["settle_time"], d1, d2)
                if period is None:
                    purged_rows[split_name(row["signal_time"], d1, d2)].append(row)
                else:
                    split_rows[period].append(row)

            for period in ("TRAIN", "VALIDATION", "TEST", "ALL"):
                if period == "ALL":
                    period_candidates = candidates
                    period_scheduled = scheduled
                else:
                    period_candidates = [x for x in candidates if split_name(x["signal_time"], d1, d2) == period]
                    period_scheduled = [x for x in scheduled if split_name(x["signal_time"], d1, d2) == period]
                for side in ("ALL", "CALL", "PUT"):
                    if side == "ALL":
                        side_candidates = period_candidates
                        side_scheduled = period_scheduled
                        side_purged = purged_rows.get(period, []) if period != "ALL" else []
                        side_rows = split_rows[period]
                    else:
                        side_candidates = [x for x in period_candidates if x["direction"] == side]
                        side_scheduled = [x for x in period_scheduled if x["direction"] == side]
                        side_purged = [x for x in purged_rows.get(period, []) if x["direction"] == side] if period != "ALL" else []
                        side_rows = [x for x in split_rows[period] if x["direction"] == side]
                    m = metrics(side_rows, bar_counts[period])
                    ci_txt = f"[{m['ci'][0]:.1f}, {m['ci'][1]:.1f}]" if m["ci"] else "n/a"
                    pf_txt = "inf" if math.isinf(m["pf"]) else f"{m['pf']:.3f}"
                    wait_txt = f"{m['wait']:.3f}%" if side == "ALL" else "—"
                    lines.append(
                        f"| {horizon*5}m | {strategy_name} | {period} | {side} | "
                        f"{len(side_candidates)} | {len(side_candidates)-len(side_scheduled)} | {len(side_purged)} | "
                        f"{m['n']} | {m['wins']}/{m['losses']}/{m['draws']} | {fmt(m['wr'])}% | {ci_txt} | "
                        f"{fmt(m['wins_all'])}% | {m['net']:+.2f} | {fmt(m['roi'])}% | {pf_txt} | "
                        f"{m['dd']:.2f} | {m['streak']} | {m['frequency']:.3f}% | {wait_txt} |"
                    )

    lines += [
        "", "## Interpretation guardrails", "",
        "- The non-overlapping table is the single-position comparison. It must not be conflated with the earlier all-trigger table, which scores every trigger as a separate stake and permits concurrent positions for expiries above 5 minutes.",
        "- The MOM3 baselines are deliberately simple, fixed and untuned. Their much higher candidate frequency is not directly comparable to the sparse BB/Williams/ADX trigger without reading frequency and WAIT.",
        "- Wilson intervals assume independent decisive outcomes. Even with within-strategy non-overlap, serial market dependence and shared regimes remain; intervals may be too narrow.",
        "- The 92% break-even decisive WR is 52.0833%. A WR above this threshold is not enough by itself; require positive net/ROI, acceptable drawdown, adequate sample, stable validation and genuinely prospective confirmation.",
        "- Do not tune on TEST or promote any rule from this exploratory historical dataset. No Desktop math core, production/stabilization branch, local files, or trading behavior is changed.", "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines)
    args.out.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
