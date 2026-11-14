#!/usr/bin/env python3
"""Tenth-wave EURUSD M5 discovery: Wilder DMI / ADX trend-state events.
Research only. Closed-bar signals, next-bar entry, exact-schedule inversion.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path

from expanded_strategy_screen import read_m1, outcome, stats
from long_history_validation import make_m5

HORIZONS = (1, 2, 3, 4, 6, 12)
PAYOUT = 0.92


def wilder_sum(values, period):
    out = [None] * len(values)
    if len(values) < period:
        return out
    total = sum(values[:period])
    out[period - 1] = total
    for i in range(period, len(values)):
        total = total - total / period + values[i]
        out[i] = total
    return out


def dmi_adx(bars, period=14):
    """Wilder +DI, -DI and ADX; no future bars are used."""
    n = len(bars)
    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up = bars[i].high - bars[i - 1].high
        down = bars[i - 1].low - bars[i].low
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(
            bars[i].high - bars[i].low,
            abs(bars[i].high - bars[i - 1].close),
            abs(bars[i].low - bars[i - 1].close),
        )
    atr_s = wilder_sum(tr, period)
    plus_s = wilder_sum(plus_dm, period)
    minus_s = wilder_sum(minus_dm, period)
    plus_di = [None] * n
    minus_di = [None] * n
    dx = [None] * n
    for i in range(period - 1, n):
        if atr_s[i] is None or atr_s[i] <= 0:
            continue
        plus_di[i] = 100.0 * plus_s[i] / atr_s[i]
        minus_di[i] = 100.0 * minus_s[i] / atr_s[i]
        denom = plus_di[i] + minus_di[i]
        dx[i] = 0.0 if denom == 0 else 100.0 * abs(plus_di[i] - minus_di[i]) / denom
    adx = [None] * n
    first = 2 * period - 2
    if n > first:
        seed = [dx[j] for j in range(period - 1, first + 1) if dx[j] is not None]
        if len(seed) == period:
            adx[first] = sum(seed) / period
            for i in range(first + 1, n):
                if dx[i] is not None:
                    adx[i] = ((period - 1) * adx[i - 1] + dx[i]) / period
    return plus_di, minus_di, adx


def discover(bars):
    plus, minus, adx = dmi_adx(bars, 14)
    events = defaultdict(list)
    for i in range(35, len(bars) - 13):
        pdi, mdi = plus[i], minus[i]
        pp, pm = plus[i - 1], minus[i - 1]
        ai, ap = adx[i], adx[i - 1]
        if None in (pdi, mdi, pp, pm, ai, ap, adx[i - 3]):
            continue
        b = bars[i]
        rising = ai > ap and ai > adx[i - 3]
        # Fresh directional movement crossover, with fixed ADX strength gates.
        bull_cross = pp <= pm and pdi > mdi and b.close > b.open
        bear_cross = pp >= pm and mdi > pdi and b.close < b.open
        for threshold in (15, 25):
            if bull_cross and ai >= threshold and rising:
                events[f"DMI_CROSS_ADX{threshold}_CALL"].append((i, "CALL"))
            if bear_cross and ai >= threshold and rising:
                events[f"DMI_CROSS_ADX{threshold}_PUT"].append((i, "PUT"))
        # Established DMI dominance with strengthening ADX and directional close.
        if ai >= 20 and rising:
            if pdi > mdi and b.close > bars[i - 1].close:
                events["DMI_TREND_ADX20_RISING_CALL"].append((i, "CALL"))
            if mdi > pdi and b.close < bars[i - 1].close:
                events["DMI_TREND_ADX20_RISING_PUT"].append((i, "PUT"))
        # ADX enters a strong-trend regime; DI direction and candle agree.
        if ap < 20 <= ai:
            if pdi > mdi and b.close > b.open:
                events["DMI_ADX20_REGIME_ENTRY_CALL"].append((i, "CALL"))
            if mdi > pdi and b.close < b.open:
                events["DMI_ADX20_REGIME_ENTRY_PUT"].append((i, "PUT"))
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    m1 = read_m1(args.data)
    segments = make_m5(m1)
    days = sorted({b.timestamp.date() for seg in segments for b in seg})
    if len(days) < 30:
        raise SystemExit("Insufficient history")
    d1, d2 = days[int(0.60 * len(days))], days[int(0.80 * len(days))]
    results = defaultdict(list)
    raw = defaultdict(int)
    purged = 0
    family_names = set()
    for bars in segments:
        ev = discover(bars)
        family_names.update(ev)
        for name, items in ev.items():
            for h in HORIZONS:
                split_rows = {"TRAIN": [], "VALIDATION": [], "TEST": []}
                for i, side in items:
                    if i + h >= len(bars):
                        continue
                    day = bars[i].timestamp.date()
                    period = "TRAIN" if day < d1 else "VALIDATION" if day < d2 else "TEST"
                    settle_day = bars[i + h].timestamp.date()
                    boundary = d1 if period == "TRAIN" else d2 if period == "VALIDATION" else None
                    if boundary and settle_day >= boundary:
                        purged += 1
                        continue
                    split_rows[period].append((i, side))
                for period, rows in split_rows.items():
                    raw[(name, h, period)] += len(rows)
                    next_allowed = -1
                    for i, side in sorted(rows):
                        if i < next_allowed:
                            continue
                        results[(name, h, period, "ORIGINAL")].append(outcome(bars, i, side, h))
                        inverse = "PUT" if side == "CALL" else "CALL"
                        results[(name, h, period, "INVERTED")].append(outcome(bars, i, inverse, h))
                        next_allowed = i + h

    lines = [
        "# Tenth-wave EURUSD M5 discovery — Wilder DMI / ADX",
        "",
        f"Source: Dukascopy EUR/USD M1 BID; valid M1 rows={len(m1):,}; M5 bars={sum(map(len, segments)):,}; gap-separated segments={len(segments)}.",
        f"Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}.",
        f"Chronological splits: TRAIN < {d1}; VALIDATION {d1}–{d2}; TEST >= {d2}; boundary-crossing outcomes purged={purged:,}.",
        "Predeclared families: fresh +DI/-DI cross with ADX >=15 or >=25 and rising; established DI dominance with ADX >=20 strengthening; ADX crossing into >=20 regime with DI/candle direction agreement.",
        "Wilder DMI/ADX(14) is computed causally from completed M5 OHLC bars. Entry next M5 open; expiry 5/10/15/20/30/60 minutes. One active position per family/expiry/segment/split.",
        "Original and inverse use identical events and schedule; only CALL/PUT flips. Payout assumption +0.92/-1/0; decisive break-even 52.083%.",
        "Dukascopy BID is not Pocket Option executable pricing. TEST has prior exploratory exposure; no result is confirmation. Multiple testing and serial dependence remain.",
        "",
        "| Family | Variant | Expiry | Split | n | W/L/D | Decisive WR | Wilson 95% CI | Net u | Max DD u | Raw events |",
        "|---|---|---:|---|---:|---|---:|---|---:|---:|---:|",
    ]
    for (name, h, period, variant), xs in sorted(results.items()):
        s = stats(xs)
        ci = s[5]
        wr = "n/a" if s[4] is None else f"{s[4]:.2f}%"
        ci_text = "n/a" if ci is None else f"[{ci[0]:.2f},{ci[1]:.2f}]%"
        lines.append(
            f"| {name} | {variant} | {h * 5}m | {period} | {s[0]} | "
            f"{s[1]}/{s[2]}/{s[3]} | {wr} | {ci_text} | {s[6]:+.2f} | {s[7]:.2f} | "
            f"{raw[(name, h, period)]} |"
        )
    lines += [
        "",
        "## Screening notes",
        "",
        "- This wave expands the candidate library; it does not profile registered candidates by market regime.",
        "- A TEST-only high win rate is not eligible for promotion. Review exact-schedule inversions for weak originals.",
        "- Prioritize meaningful VALIDATION samples and consistency across TRAIN/VALIDATION/TEST; 56.0–56.9% is borderline, not a pass.",
        "- Wilson intervals do not account for serial dependence; broad screening creates multiple-testing risk.",
        "- Any follow-up context hypothesis must be frozen before a genuinely untouched forward sample.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"Tenth-wave complete: M1={len(m1):,}; M5={sum(map(len, segments)):,}; "
        f"families={len(family_names)}; rows={len(results)}; report={args.out}"
    )


if __name__ == "__main__":
    main()
