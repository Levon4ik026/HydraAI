#!/usr/bin/env python3
"""Predeclared sensitivity check for the locked NY PUT matched-control study.

Tests whether the paired advantage depends on selecting the single nearest
feature-distance control. For each frozen, non-overlapping candidate, repeatedly
draws a control at random from the same segment/date/hour/split and within +/-12
M5 bars, with no control reuse and no overlapping control outcome windows.
No thresholds or candidate definitions are changed.
"""
from __future__ import annotations
import argparse, math, random
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from long_history_validation import read_duka, make_events, m5_close_time
from reproduce_m5_bb_williams_adx import make_m5, indicators

NY = ZoneInfo("America/New_York")
H = 4
PAYOUT = 0.92
REPS = 5000
SEED = 314159


def period(ts, end, d1, d2):
    if ts.date() < d1:
        return None if end.date() >= d1 else "TRAIN"
    if ts.date() < d2:
        return None if end.date() >= d2 else "VALIDATION"
    return "TEST"


def pnl(outcome):
    return PAYOUT if outcome == "WIN" else -1.0 if outcome == "LOSS" else 0.0


def outcome(bars, i):
    delta = bars[i + H].close - bars[i + 1].open
    return "DRAW" if abs(delta) < 1e-12 else "WIN" if delta < 0 else "LOSS"


def summarize(rows):
    w = sum(x == "WIN" for x in rows)
    l = sum(x == "LOSS" for x in rows)
    d = sum(x == "DRAW" for x in rows)
    n = w + l
    return w, l, d, (100*w/n if n else float("nan")), sum(map(pnl, rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/NY_PUT_MATCH_SENSITIVITY.md"))
    args = ap.parse_args()

    m1 = read_duka(args.data)
    segments = make_m5(m1)
    events = make_events(segments, 15)
    event_map = {(e["segment"], e["bar_index"]): e for e in events}
    event_keys = set(event_map)
    event_days = sorted({e["signal_time"].date() for e in events})
    d1, d2 = event_days[int(.60 * len(event_days))], event_days[int(.80 * len(event_days))]

    candidates, controls = [], []
    for sid, bars in enumerate(segments):
        ind = indicators(bars)
        for i in range(50, len(bars) - H):
            ts = bars[i].timestamp
            local = ts.astimezone(NY)
            if not 8 <= local.hour < 13:
                continue
            x = ind[i]
            if x["adx"] is None or x["plus_di"] is None or x["minus_di"] is None:
                continue
            if not (x["adx"] >= 25 and x["plus_di"] > x["minus_di"] and bars[i].close > bars[i-12].close):
                continue
            end = m5_close_time(bars[i+H].timestamp)
            split = period(ts, end, d1, d2)
            if split is None:
                continue
            r = {
                "sid": sid, "i": i, "date": local.date(), "hour": local.hour,
                "period": split, "outcome": outcome(bars, i)
            }
            if (sid, i) in event_keys:
                e = event_map[(sid, i)]
                if e["direction"] == "PUT":
                    candidates.append(r)
            else:
                controls.append(r)

    # Freeze one-position candidate schedule exactly as in the primary audit.
    byseg = defaultdict(list)
    for r in candidates:
        byseg[r["sid"]].append(r)
    chosen = []
    for sid, rs in byseg.items():
        allowed = -1
        for r in sorted(rs, key=lambda z: z["i"]):
            if r["i"] >= allowed:
                chosen.append(r)
                allowed = r["i"] + H

    # Controls may not overlap any candidate's outcome window.
    cand_intervals = defaultdict(list)
    for r in candidates:
        cand_intervals[r["sid"]].append((r["i"] + 1, r["i"] + H))
    def overlaps_candidate(q):
        return any(not (q["i"] + H < a or q["i"] + 1 > b)
                   for a, b in cand_intervals[q["sid"]])
    pool = [q for q in controls if not overlaps_candidate(q)]

    bykey = defaultdict(list)
    for q in pool:
        bykey[(q["sid"], q["date"], q["hour"], q["period"])].append(q)

    # Eligible local controls are fixed before simulation; selection is random,
    # without replacement, and outcome-blind.
    options = {}
    for cidx, c in enumerate(sorted(chosen, key=lambda z: (z["date"], z["hour"], z["sid"], z["i"]))):
        key = (c["sid"], c["date"], c["hour"], c["period"])
        options[cidx] = [q for q in bykey.get(key, [])
                         if abs(q["i"] - c["i"]) <= 12]
    ordered = sorted(chosen, key=lambda z: (z["date"], z["hour"], z["sid"], z["i"]))
    cand_outcomes = [c["outcome"] for c in ordered]

    # Nearest-control baseline is deterministic, same greedy chronological
    # no-reuse / non-overlap constraints as the primary matched-control audit.
    # For sensitivity, report random-control distribution under those constraints.
    rng = random.Random(SEED)
    split_samples = {p: [] for p in ("TRAIN", "VALIDATION", "TEST", "ALL")}
    matched_counts = []
    for rep in range(REPS):
        used = set()
        selected_pairs = []
        for cidx, c in enumerate(ordered):
            opts = []
            for q in options[cidx]:
                qid = (q["sid"], q["i"])
                if qid in used:
                    continue
                if any(q["sid"] == prev["sid"] and
                       not (q["i"] + H < prev["i"] + 1 or q["i"] + 1 > prev["i"] + H)
                       for _, prev in selected_pairs):
                    continue
                opts.append(q)
            if not opts:
                continue
            q = rng.choice(opts)
            used.add((q["sid"], q["i"]))
            selected_pairs.append((c, q))
        matched_counts.append(len(selected_pairs))
        bysplit = defaultdict(list)
        for c, q in selected_pairs:
            bysplit[c["period"]].append(pnl(c["outcome"]) - pnl(q["outcome"]))
        for p in ("TRAIN", "VALIDATION", "TEST"):
            vals = bysplit[p]
            if vals:
                split_samples[p].append(sum(vals) / len(vals))
        if selected_pairs:
            all_diff = [pnl(c["outcome"]) - pnl(q["outcome"])
                        for c, q in selected_pairs]
            split_samples["ALL"].append(sum(all_diff) / len(all_diff))

    # A deterministic nearest match for comparison, with identical constraints.
    # It is intentionally reconstructed independently and not tuned.
    used = set()
    nearest = []
    for c in ordered:
        opts = []
        for q in options[ordered.index(c)]:
            qid = (q["sid"], q["i"])
            if qid in used:
                continue
            if any(q["sid"] == prev["sid"] and
                   not (q["i"] + H < prev["i"] + 1 or q["i"] + 1 > prev["i"] + H)
                   for prev in nearest):
                continue
            # No outcome-based choice: nearest in time to candidate.
            opts.append((abs(q["i"] - c["i"]), q))
        if not opts:
            continue
        q = min(opts, key=lambda x: x[0])[1]
        used.add((q["sid"], q["i"]))
        nearest.append(q)

    lines = [
        "# HYDRA — NY PUT random matched-control sensitivity",
        "",
        f"Data: Dukascopy EURUSD M1 BID; M1 rows={len(m1):,}; M5 bars={sum(map(len, segments)):,}; segments={len(segments):,}.",
        f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
        f"Split: TRAIN < {d1}; VALIDATION < {d2}; TEST >= {d2}.",
        "Frozen candidate: NY 08:00–12:59, frozen BB/Williams/ADX PUT event, ADX>=25, +DI>-DI, positive 12-bar momentum.",
        "Candidates use one-position non-overlap schedule. Controls are non-signal bars in the same segment, NY date, hour and split, within +/-12 M5 bars; controls overlapping any candidate outcome are excluded.",
        f"Random matching: {REPS} repetitions; one control per candidate where possible; no control reuse; no overlapping control outcomes; selection is outcome-blind.",
        "This is a control-selection sensitivity analysis, not a new independent test. Payout=92%; entry next M5 open; settle fourth following M5 close.",
        "",
        "## Candidate reference performance",
        "",
        "| Split | n | W/L/D | WR | Net |",
        "|---|---:|---:|---:|---:|",
    ]
    for split in ("TRAIN", "VALIDATION", "TEST", "ALL"):
        inds = [i for i, c in enumerate(ordered) if split == "ALL" or c["period"] == split]
        w,l,d,wr,n = summarize([cand_outcomes[i] for i in inds])
        lines.append(f"| {split} | {len(inds)} | {w}/{l}/{d} | {wr:.2f}% | {n:+.2f}u |")

    lines += [
        "",
        "## Random-control paired difference distribution",
        "",
        "| Split | Repetitions | Mean diff/pair | 2.5th percentile | Median | 97.5th percentile |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for split in ("TRAIN", "VALIDATION", "TEST", "ALL"):
        vals = sorted(split_samples[split])
        if not vals:
            lines.append(f"| {split} | 0 | n/a | n/a | n/a | n/a |")
            continue
        def quantile(q):
            return vals[min(len(vals)-1, int(q*(len(vals)-1)))]
        lines.append(f"| {split} | {len(vals)} | {sum(vals)/len(vals):+.3f}u | {quantile(.025):+.3f}u | {quantile(.5):+.3f}u | {quantile(.975):+.3f}u |")

    lines += [
        "",
        "## Match availability",
        "",
        f"- Frozen one-position candidates: {len(ordered)}.",
        f"- Mean random matched controls: {sum(matched_counts)/len(matched_counts):.1f} of {len(ordered)}.",
        f"- 2.5th–97.5th percentile matched count: {sorted(matched_counts)[int(.025*(len(matched_counts)-1))]}–{sorted(matched_counts)[int(.975*(len(matched_counts)-1))]}.",
        f"- Deterministic nearest-in-time matching produced {len(nearest)} controls (a diagnostic comparator, not optimized).",
        "",
        "## Interpretation guardrails",
        "",
        "- A robust positive result should remain positive across random control selections, especially in TEST; a wide distribution or low match rate means the apparent edge is sensitive to control choice.",
        "- The candidate was discovered in earlier exploratory work; this remains retrospective validation, not prospective confirmation.",
        "- Do not tune thresholds, time windows, or matching rules against these outputs. No production or local files are changed; no orders are placed.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"candidates={len(ordered)}; pool={len(pool)}; wrote {args.out}")


if __name__ == "__main__":
    main()
