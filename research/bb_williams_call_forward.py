#!/usr/bin/env python3
"""Locked forward-only audit for the BB/Williams/ADX CALL 5m candidate."""
from __future__ import annotations
import argparse, csv, json, math, random
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

from reproduce_m5_bb_williams_adx import Bar, make_m5, build_signals

UTC = timezone.utc
FORWARD_START = datetime(2026, 10, 29, 0, 0, tzinfo=UTC)
PAYOUT = 0.92
ADX_MIN = 15.0
BOOTSTRAPS = 5000
SEED = 20261116


def parse_timestamp(raw: str) -> datetime:
    value = raw.strip()
    try:
        number = float(value)
        if abs(number) > 1_000_000_000_000:
            number /= 1000.0
        return datetime.fromtimestamp(number, UTC)
    except ValueError:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        return stamp.astimezone(UTC)


def load_m1(path: Path):
    parsed = {}
    invalid = duplicates = conflicting = 0
    raw_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = {x.strip().lower(): x for x in (reader.fieldnames or [])}
        timestamp_col = next((columns[x] for x in ("timestamp", "datetime", "datetime_utc", "date")
                              if x in columns), None)
        if timestamp_col is None or not all(x in columns for x in ("open", "high", "low", "close")):
            raise ValueError(f"Unsupported M1 CSV header: {reader.fieldnames}")
        for row in reader:
            raw_rows += 1
            try:
                ts = parse_timestamp(row[timestamp_col])
                o, h, l, c = [float(row[columns[x]]) for x in ("open", "high", "low", "close")]
                if ts.second != 0 or ts.microsecond != 0:
                    raise ValueError("M1 timestamp is not minute-aligned")
                if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                    raise ValueError("non-finite or non-positive OHLC")
                if h < max(o, l, c) or l > min(o, c):
                    raise ValueError("invalid OHLC ordering")
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                invalid += 1
                continue
            values = (o, h, l, c)
            old = parsed.get(ts)
            if old is not None:
                duplicates += 1
                if old != values:
                    conflicting += 1
                    raise ValueError(f"Conflicting duplicate timestamp: {ts.isoformat()}")
                continue
            parsed[ts] = values
    if not parsed:
        raise ValueError("No valid M1 rows")
    bars = [Bar(ts, *parsed[ts]) for ts in sorted(parsed)]
    gaps = []
    for previous, current in zip(bars, bars[1:]):
        minutes = int((current.timestamp - previous.timestamp).total_seconds() // 60)
        if minutes > 1:
            gaps.append(minutes - 1)
    buckets = defaultdict(list)
    for bar in bars:
        start = bar.timestamp.replace(minute=(bar.timestamp.minute // 5) * 5, second=0, microsecond=0)
        buckets[start].append(bar.timestamp)
    incomplete = 0
    for start, stamps in buckets.items():
        expected = [start + timedelta(minutes=i) for i in range(5)]
        if sorted(stamps) != expected:
            incomplete += 1
    integrity = {
        "raw_rows": raw_rows, "valid_unique_rows": len(bars), "invalid_rows": invalid,
        "duplicate_rows": duplicates, "conflicting_duplicates": conflicting,
        "first_utc": bars[0].timestamp.isoformat(), "last_utc": bars[-1].timestamp.isoformat(),
        "m1_gap_intervals": len(gaps), "m1_missing_minutes": sum(gaps),
        "largest_m1_gap_minutes": max(gaps, default=0), "incomplete_m5_buckets": incomplete,
    }
    return bars, integrity


def outcome(entry_open: float, settlement_close: float, side: str) -> str:
    delta = settlement_close - entry_open
    if abs(delta) < 1e-12:
        return "DRAW"
    return "WIN" if ((delta > 0) == (side == "CALL")) else "LOSS"


def pnl(result: str) -> float:
    return PAYOUT if result == "WIN" else -1.0 if result == "LOSS" else 0.0


def wilson(wins: int, decisive: int):
    if decisive <= 0:
        return None
    z = 1.959963984540054
    p = wins / decisive
    den = 1 + z*z/decisive
    center = (p + z*z/(2*decisive)) / den
    half = z * math.sqrt(p*(1-p)/decisive + z*z/(4*decisive*decisive)) / den
    return [100*(center-half), 100*(center+half)]


def summarize(rows):
    ordered = sorted(rows, key=lambda x: x["entry_time"])
    w = sum(x["outcome"] == "WIN" for x in ordered)
    l = sum(x["outcome"] == "LOSS" for x in ordered)
    d = len(ordered) - w - l
    dec = w + l
    net = w*PAYOUT - l
    eq = peak = dd = 0.0
    streak = max_streak = 0
    for row in ordered:
        eq += pnl(row["outcome"])
        peak = max(peak, eq)
        dd = max(dd, peak-eq)
        streak = streak+1 if row["outcome"] == "LOSS" else 0
        max_streak = max(max_streak, streak)
    pf = (w*PAYOUT/l) if l else (float("inf") if w else None)
    return {
        "n": len(ordered), "w": w, "l": l, "d": d,
        "wr": 100*w/dec if dec else None,
        "wins_all": 100*w/len(ordered) if ordered else None,
        "wilson": wilson(w, dec), "net": net,
        "roi": 100*net/len(ordered) if ordered else None,
        "pf": pf, "max_dd": dd, "max_loss_streak": max_streak,
        "active_days": len({x["entry_time"].date() for x in ordered}),
    }


def daily_bootstrap(rows, last_day):
    days = []
    day = FORWARD_START.date()
    while day <= last_day:
        days.append(day)
        day += timedelta(days=1)
    if not days:
        return None
    daily = defaultdict(float)
    for row in rows:
        daily[row["entry_time"].date()] += pnl(row["outcome"])
    values = [daily[d] for d in days]
    rng = random.Random(SEED)
    samples = []
    positive = 0
    for _ in range(BOOTSTRAPS):
        total = sum(values[rng.randrange(len(values))] for _ in values)
        samples.append(total)
        positive += total > 0
    samples.sort()
    return {
        "days": len(days), "ci95_net": [samples[int(.025*BOOTSTRAPS)], samples[int(.975*BOOTSTRAPS)]],
        "prob_net_positive_pct": 100*positive/BOOTSTRAPS,
        "method": "UTC calendar-day bootstrap with replacement; within-day clustering retained, multi-day dependence not removed",
    }


def fmt(value, digits=2, suffix=""):
    return "n/a" if value is None else f"{value:.{digits}f}{suffix}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research-artifacts/bb-williams-call-forward/report.md"))
    ap.add_argument("--ledger", type=Path, default=Path("research-artifacts/bb-williams-call-forward/trades.csv"))
    args = ap.parse_args()

    m1, integrity = load_m1(args.data)
    segments = make_m5(m1)
    rows = build_signals(segments)
    all_call, all_put, background = [], [], []
    eligible_bars = 0
    for i in range(len(rows)-1):
        cur, nxt = rows[i], rows[i+1]
        if cur["segment_id"] != nxt["segment_id"]:
            continue
        if nxt["bar"].timestamp - cur["bar"].timestamp != timedelta(minutes=5):
            continue
        signal_available = cur["bar"].timestamp + timedelta(minutes=5)
        entry_time = nxt["bar"].timestamp
        settlement_time = entry_time + timedelta(minutes=5)
        if signal_available < FORWARD_START or entry_time < FORWARD_START:
            continue
        eligible_bars += 1
        adx = cur.get("adx")
        if adx is None or adx < ADX_MIN:
            continue
        if cur["signal"] == 1:
            result = outcome(nxt["bar"].open, nxt["bar"].close, "CALL")
            all_call.append({
                "signal_time": signal_available, "entry_time": entry_time,
                "settlement_time": settlement_time, "entry_price": nxt["bar"].open,
                "settlement_price": nxt["bar"].close, "outcome": result,
                "adx": adx, "segment_id": cur["segment_id"],
            })
        elif cur["signal"] == -1:
            result = outcome(nxt["bar"].open, nxt["bar"].close, "PUT")
            all_put.append({
                "signal_time": signal_available, "entry_time": entry_time,
                "settlement_time": settlement_time, "entry_price": nxt["bar"].open,
                "settlement_price": nxt["bar"].close, "outcome": result,
                "adx": adx, "segment_id": cur["segment_id"],
            })
        else:
            result = outcome(nxt["bar"].open, nxt["bar"].close, "CALL")
            background.append({
                "signal_time": signal_available, "entry_time": entry_time,
                "settlement_time": settlement_time, "entry_price": nxt["bar"].open,
                "settlement_price": nxt["bar"].close, "outcome": result,
                "adx": adx, "segment_id": cur["segment_id"],
            })

    # Matched PUT is the opposite direction on exactly the CALL timestamps.
    matched_put = []
    for row in all_call:
        inv = "LOSS" if row["outcome"] == "WIN" else "WIN" if row["outcome"] == "LOSS" else "DRAW"
        matched_put.append({**row, "outcome": inv})
    last_day = m1[-1].timestamp.date()
    call_stats = summarize(all_call)
    put_stats = summarize(all_put)
    matched_stats = summarize(matched_put)
    background_stats = summarize(background)
    boot = daily_bootstrap(all_call, last_day)
    frequency = 100*len(all_call)/eligible_bars if eligible_bars else 0.0
    wait = 100-frequency
    ci = call_stats["wilson"]
    if call_stats["n"] < 100:
        status = "INSUFFICIENT_FORWARD_SAMPLE"
    elif (call_stats["wr"] is not None and call_stats["wr"] >= 57 and call_stats["net"] > 0
          and call_stats["pf"] is not None and call_stats["pf"] > 1
          and ci is not None and ci[0] > (100*1/(1+PAYOUT))):
        status = "PRELIMINARILY_PROMISING_NOT_CONFIRMED"
    else:
        status = "REVIEW_THRESHOLD_NOT_MET"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    fields = ["signal_time_utc", "entry_time_utc", "settlement_time_utc", "entry_price",
              "settlement_price", "outcome", "adx", "segment_id"]
    with args.ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in all_call:
            writer.writerow({
                "signal_time_utc": row["signal_time"].isoformat(),
                "entry_time_utc": row["entry_time"].isoformat(),
                "settlement_time_utc": row["settlement_time"].isoformat(),
                "entry_price": row["entry_price"], "settlement_price": row["settlement_price"],
                "outcome": row["outcome"], "adx": row["adx"], "segment_id": row["segment_id"],
            })

    def table_row(name, s):
        ci_text = "n/a" if s["wilson"] is None else f'[{s["wilson"][0]:.2f}, {s["wilson"][1]:.2f}]%'
        return (f'| {name} | {s["n"]} | {s["w"]}/{s["l"]}/{s["d"]} | {fmt(s["wr"],2,"%")} | '
                f'{fmt(s["wins_all"],2,"%")} | {s["net"]:+.2f}u | {fmt(s["roi"],2,"%")} | '
                f'{fmt(s["pf"],3)} | {s["max_dd"]:.2f}u | {s["max_loss_streak"]} | {ci_text} |')
    lines = [
        "# Locked BB/Williams/ADX CALL 5m — prospective forward audit", "",
        f'- Source: Dukascopy EURUSD M1 BID; raw rows={integrity["raw_rows"]:,}; valid unique M1={integrity["valid_unique_rows"]:,}; invalid={integrity["invalid_rows"]:,}; duplicates={integrity["duplicate_rows"]:,}.',
        f'- M1 coverage: {integrity["first_utc"]} — {integrity["last_utc"]}.',
        f'- M1 gaps: {integrity["m1_gap_intervals"]} intervals; {integrity["m1_missing_minutes"]:,} missing minutes; largest={integrity["largest_m1_gap_minutes"]}m; incomplete M5 buckets excluded={integrity["incomplete_m5_buckets"]}.',
        f'- Complete M5 bars={sum(len(x) for x in segments):,}; continuity segments={len(segments):,}.',
        f'- Forward boundary: {FORWARD_START.isoformat()} inclusive; first scored entry must be on/after the boundary.',
        '- Frozen rule: BB(20, 2 population SD) lower-band re-entry + Williams %R(14) upward cross of -80 + Wilder ADX(14) >= 15; CALL only.',
        '- Signal is known after the completed M5 close; entry next M5 open; expiry 5m; settlement at the entry M5 close.',
        f'- Forward M5 opportunities with a contiguous next bar={eligible_bars:,}; CALL triggers={len(all_call):,}; PUT triggers ignored={len(all_put):,}; CALL frequency={frequency:.4f}%; WAIT={wait:.4f}%.',
        '- All CALL signals are evaluated; signals can be adjacent. Same-day/serial dependence is not removed.',
        f'- Payout: WIN +{PAYOUT:.2f}u, LOSS -1u, DRAW 0u; break-even decisive WR={100/(1+PAYOUT):.4f}%.',
        '- Execution caveat: BID candles are not Pocket Option executable quotes; spread, platform quote construction, actual payout, latency and settlement are not modeled.',
        '', '## Results', '',
        '| Series | N | W/L/D | Decisive WR | Wins / all | Net @92% | ROI/trade | PF | Max DD | Max loss streak | Wilson 95% |',
        '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|',
        table_row("CALL candidate", call_stats),
        table_row("PUT diagnostic (not traded)", put_stats),
        table_row("Matched PUT on CALL timestamps", matched_stats),
        table_row("Non-signal ADX>=15 background CALL", background_stats),
        '',
        '## Daily block bootstrap', '',
        f'- CALL net 95% UTC-day bootstrap interval: [{boot["ci95_net"][0]:+.2f}, {boot["ci95_net"][1]:+.2f}]u across {boot["days"]} calendar days.',
        f'- Bootstrap P(net>0): {boot["prob_net_positive_pct"]:.1f}%. {boot["method"]}.',
        '',
        '## Decision', '',
        f'- Status: **{status}**.',
        '- The prior October sample is discovery data, not prospective evidence. This report scores only entries from 2026-10-29 onward.',
        '- Minimum review threshold is 100 forward CALL trades; preliminary promise additionally requires WR>=57%, positive net, PF>1 and Wilson lower bound above break-even.',
        '- No parameter, direction, expiry or threshold may be changed from these forward observations.',
        '- Research only: no live trades, OTC, production promotion or automatic execution.',
        '',
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f'BB/Williams/ADX forward audit: M1={len(m1)} M5={sum(len(x) for x in segments)} CALL={call_stats["n"]} PUT_diag={put_stats["n"]} status={status}')


if __name__ == "__main__":
    main()
