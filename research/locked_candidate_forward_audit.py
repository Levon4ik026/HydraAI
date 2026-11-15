#!/usr/bin/env python3
"""Locked prospective audit for two preselected EURUSD M5 candidates.

No parameter search is performed. Only signals settling after the frozen cutoff
are scored. Exact opposite-direction outcomes are a matched baseline.
"""
from __future__ import annotations
import argparse, random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from standalone_strategy_screen import read_m1, build_specs, signals_for_segment, outcome
from long_history_validation import make_m5

PAYOUT = 0.92
CUTOFF = date(2026, 11, 8)  # first eligible signal day is 2026-11-09
HORIZON = 3  # 15 minutes
CANDIDATES = (
    "MEAN_REV_20_Z2.0_PUT",
    "MEAN_REV_40_Z2.0_PUT",
)
BOOTSTRAPS = 5000
SEED = 20261115


def pnl(x):
    return PAYOUT if x == "W" else -1.0 if x == "L" else 0.0


def stats(rows):
    outcomes = [r[1] for r in rows]
    w = outcomes.count("W"); l = outcomes.count("L"); d = outcomes.count("D")
    dec = w + l
    wr = 100*w/dec if dec else None
    net = w*PAYOUT-l
    pf = w*PAYOUT/l if l else (float("inf") if w else 0.0)
    eq = peak = dd = 0.0; streak = max_streak = 0
    for x in outcomes:
        eq += pnl(x); peak = max(peak, eq); dd = max(dd, peak-eq)
        streak = streak+1 if x == "L" else 0
        max_streak = max(max_streak, streak)
    return dict(n=len(rows), w=w, l=l, d=d, wr=wr, net=net,
                roi=100*net/len(rows) if rows else None, pf=pf,
                max_dd=dd, max_loss_streak=max_streak)


def bootstrap_day_ci(rows, calendar_days, seed):
    by_day = defaultdict(float)
    for day, result in rows:
        by_day[day] += pnl(result)
    vals = [by_day[d] for d in calendar_days]  # retain zero-trade days
    if not vals:
        return None, None
    rng = random.Random(seed)
    n = len(vals)
    samples = []
    for _ in range(BOOTSTRAPS):
        samples.append(sum(vals[rng.randrange(n)] for _ in range(n)))
    samples.sort()
    return samples[int(0.025*BOOTSTRAPS)], samples[min(BOOTSTRAPS-1, int(0.975*BOOTSTRAPS))]


def fmt(s):
    if s["wr"] is None:
        wr = "n/a"
    else:
        wr = f'{s["wr"]:.2f}%'
    pf = "inf" if s["pf"] == float("inf") else f'{s["pf"]:.3f}'
    roi = "n/a" if s["roi"] is None else f'{s["roi"]:+.2f}%'
    return (f'{s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {wr} | '
            f'{s["net"]:+.2f}u | {roi} | {pf} | {s["max_dd"]:.2f}u | '
            f'{s["max_loss_streak"]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research/LOCKED_CANDIDATE_FORWARD_AUDIT.md"))
    a = ap.parse_args()

    m1 = read_m1(a.data)
    segments = make_m5(m1)
    specs = [s for s in build_specs() if s[0] in CANDIDATES]
    rows = {name: [] for name in CANDIDATES}
    raw_counts = {name: 0 for name in CANDIDATES}
    total_m5 = sum(map(len, segments))
    for seg_id, bars in enumerate(segments):
        signals = signals_for_segment(bars, specs)
        for name in CANDIDATES:
            events = signals.get(name, [])
            raw_counts[name] += sum(1 for i, _ in events
                                    if bars[i].timestamp.date() > CUTOFF)
            next_allowed = -1
            for i, side in events:
                if bars[i].timestamp.date() <= CUTOFF:
                    continue
                if i + HORIZON >= len(bars) or i < next_allowed:
                    continue
                settle_time = bars[i+HORIZON].timestamp + timedelta(minutes=5)
                if settle_time.date() <= CUTOFF:
                    continue
                result = outcome(bars, i, side, HORIZON)
                rows[name].append((bars[i].timestamp.date(), result, side,
                                   bars[i].timestamp.isoformat(),
                                   bars[i+1].timestamp.isoformat()))
                next_allowed = i + HORIZON

    all_days = []
    if m1:
        d = CUTOFF + timedelta(days=1)
        end = m1[-1].timestamp.date()
        while d <= end:
            all_days.append(d)
            d += timedelta(days=1)

    lines = [
        "# Locked prospective candidate audit",
        "",
        f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} valid M1 rows; "
        f"{total_m5:,} complete M5 bars; {len(segments):,} gap-separated segments.",
        f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
        f"Frozen cutoff: {CUTOFF.isoformat()} inclusive. Eligible signals begin "
        f"{(CUTOFF + timedelta(days=1)).isoformat()}.",
        "Candidates and all parameters were selected before this forward period; "
        "this script performs no optimization or ranking.",
        "Exact rules: prior-40 or prior-20 completed M5 close mean and population "
        "standard deviation; z-score is computed from bars strictly before the signal bar. "
        "PUT signal when z >= 2.0 and the completed signal candle is bearish and closes "
        "below the previous close. CALL counterpart when z <= -2.0 and the completed "
        "signal candle is bullish and closes above the previous close.",
        "Entry: next M5 open. Expiry: close of the third subsequent M5 bar (15 minutes). "
        "One position at a time per candidate and gap-separated segment.",
        "Payout: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%.",
        "Matched baseline: exact same candidate timestamps and entries, but opposite direction. "
        "BID candles are not Pocket Option executable quotes; spread, payout variation, "
        "latency and platform-price differences are not modeled.",
        "Daily bootstrap: 5,000 resamples of UTC calendar days with replacement, including "
        "zero-trade days. This preserves within-day clustering, not multi-day dependence.",
        "",
        "## Forward results",
        "",
        "| Candidate | Trades W/L/D | Decisive WR | Net | ROI/trade | PF | Max DD | Max loss streak | Raw signals | Active/calendar days | Daily bootstrap 95% CI net | P(net>0) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rng = random.Random(SEED)
    for name in CANDIDATES:
        candidate_rows = rows[name]
        base = [(day, res) for day, res, *_ in candidate_rows]
        inverse = [(day, "L" if res == "W" else "W" if res == "L" else "D")
                   for day, res, *_ in candidate_rows]
        s = stats([(day, res) for day, res, *_ in candidate_rows])
        lo, hi = bootstrap_day_ci(base, all_days, SEED + CANDIDATES.index(name))
        # Matched opposite-side baseline is reported below, not used to select.
        active = len({day for day, *_ in candidate_rows})
        prob = None
        if all_days:
            by_day = defaultdict(float)
            for day, res in base:
                by_day[day] += pnl(res)
            vals = [by_day[d] for d in all_days]
            positives = 0
            for _ in range(BOOTSTRAPS):
                positives += sum(vals[rng.randrange(len(vals))] for _ in range(len(vals))) > 0
            prob = 100*positives/BOOTSTRAPS
        ci = "n/a" if lo is None else f"[{lo:+.2f}, {hi:+.2f}]u"
        prob_txt = "n/a" if prob is None else f"{prob:.1f}%"
        wr_txt = "n/a" if s["wr"] is None else f"{s['wr']:.2f}%"
        roi_txt = "n/a" if s["roi"] is None else f"{s['roi']:+.2f}%"
        pf_txt = "inf" if s["pf"] == float("inf") else f"{s['pf']:.3f}"
        lines.append(f"| {name} | {s['n']} ({s['w']}/{s['l']}/{s['d']}) | "
                     f"{wr_txt} | {s['net']:+.2f}u | {roi_txt} | {pf_txt} | "
                     f"{s['max_dd']:.2f}u | {s['max_loss_streak']} | "
                     f"{raw_counts[name]} | {active}/{len(all_days)} | {ci} | {prob_txt} |")

    lines += ["", "## Matched opposite-direction baseline", "",
              "| Candidate | Trades W/L/D | Decisive WR | Net | PF |",
              "|---|---:|---:|---:|---:|"]
    for name in CANDIDATES:
        inv = [(day, "L" if res == "W" else "W" if res == "L" else "D")
               for day, res, *_ in rows[name]]
        s = stats(inv)
        wr_txt = "n/a" if s["wr"] is None else f"{s['wr']:.2f}%"
        pf_txt = "inf" if s["pf"] == float("inf") else f"{s['pf']:.3f}"
        lines.append(f"| {name} reversed | {s['n']} ({s['w']}/{s['l']}/{s['d']}) | "
                     f"{wr_txt} | {s['net']:+.2f}u | {pf_txt} |")

    lines += ["", "## Daily forward ledger", "",
              "| Signal UTC day | Candidate | Side | Signal time UTC | Entry time UTC | Outcome |",
              "|---|---|---|---|---|---|"]
    for name in CANDIDATES:
        for day, result, side, sig, entry in sorted(rows[name], key=lambda x: x[3]):
            lines.append(f"| {day} | {name} | {side} | {sig} | {entry} | {result} |")
    lines += ["", "## Decision rule", "",
              "- This is a prospective monitoring report, not a new search.",
              "- Fewer than 100 forward trades per candidate is explicitly insufficient for any promotion decision.",
              "- A positive point estimate with a bootstrap interval spanning zero is inconclusive.",
              "- Neither candidate is approved for production or automatic execution by this report.",
              "- No live trades are opened; this is analysis only.", ""]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {a.out}; M1={len(m1)}; M5={total_m5}; forward_cutoff={CUTOFF}; "
          + "; ".join(f"{n}: raw={raw_counts[n]}, accepted={len(rows[n])}" for n in CANDIDATES))


if __name__ == "__main__":
    main()
