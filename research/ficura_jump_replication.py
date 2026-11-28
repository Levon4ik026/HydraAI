#!/usr/bin/env python3
"""Frozen-parameter Fičura (2019) EUR/USD jump replication and binary adaptation.

Research-only. Signals use completed bars; executable entry is next bar open.
No parameter optimization is performed. CSV must be Dukascopy-style M1 BID:
timestamp (Unix ms), open, high, low, close.
"""
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from lee_mykland_jump import detect_jumps

PAYOUT = 0.92
BINARY_HORIZONS = (1, 2, 3, 5, 8)
# Fičura (2019), Table 3: frozen EUR/USD OOS selections.
SOURCE_PARAMS = {
    1: (64, 0.999, 1),
    5: (128, 0.999, 16),
    15: (64, 0.90, 16),
    30: (32, 0.95, 16),
}


@dataclass(frozen=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float


def load_m1(path: Path) -> list[Bar]:
    rows: dict[datetime, Bar] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"timestamp", "open", "high", "low", "close"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Expected {sorted(required)}, got {reader.fieldnames}")
        for row in reader:
            try:
                ts = datetime.fromtimestamp(int(float(row["timestamp"])) / 1000, tz=timezone.utc)
                o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
                if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                    continue
                if h < max(o, l, c) or l > min(o, c):
                    continue
                rows[ts] = Bar(ts, o, h, l, c)
            except (ValueError, OverflowError):
                continue
    return [rows[t] for t in sorted(rows)]


def make_bars(m1: list[Bar], minutes: int) -> list[Bar]:
    if minutes == 1:
        return m1
    groups: dict[datetime, list[Bar]] = {}
    for bar in m1:
        epoch_min = int(bar.ts.timestamp() // 60)
        bucket_min = epoch_min - epoch_min % minutes
        bucket = datetime.fromtimestamp(bucket_min * 60, tz=timezone.utc)
        groups.setdefault(bucket, []).append(bar)
    out = []
    for ts, group in sorted(groups.items()):
        if len(group) != minutes:
            continue
        if any((group[i].ts - group[i-1].ts).total_seconds() != 60 for i in range(1, minutes)):
            continue
        if group[0].ts != ts:
            continue
        out.append(Bar(ts, group[0].open, max(x.high for x in group),
                       min(x.low for x in group), group[-1].close))
    return out


def split_segments(bars: list[Bar], seconds: int) -> list[list[Bar]]:
    segments: list[list[Bar]] = []
    current: list[Bar] = []
    for bar in bars:
        if current and (bar.ts - current[-1].ts).total_seconds() != seconds:
            if current:
                segments.append(current)
            current = []
        current.append(bar)
    if current:
        segments.append(current)
    return segments


def wilson(w: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z = 1.959963984540054
    p = w / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return 100*(center-half), 100*(center+half)


def binary_stats(records: list[dict], payout: float) -> dict:
    wins = sum(x["outcome"] == "WIN" for x in records)
    losses = sum(x["outcome"] == "LOSS" for x in records)
    draws = sum(x["outcome"] == "DRAW" for x in records)
    decisive = wins + losses
    lo, hi = wilson(wins, decisive)
    return {"n": len(records), "w": wins, "l": losses, "d": draws,
            "wr": 100*wins/decisive if decisive else float("nan"),
            "lo": lo, "hi": hi, "net": wins*payout-losses}


def make_events(segments: list[list[Bar]], k: int, p: float, total_returns: int):
    events = []
    global_index = 0
    for sid, seg in enumerate(segments):
        found = detect_jumps([b.close for b in seg], k=k, confidence=p,
                             threshold_n=max(3, total_returns))
        for jump in found:
            events.append({"sid": sid, "i": jump.index, "global": global_index + jump.index,
                           "ts": seg[jump.index].ts, "direction": jump.direction,
                           "l": jump.l_statistic, "threshold": jump.threshold})
        global_index += len(seg)
    return sorted(events, key=lambda x: x["global"])


def nonoverlap(events: list[dict], horizon: int) -> list[dict]:
    selected = []
    next_allowed: dict[int, int] = {}
    for event in events:
        sid, i = event["sid"], event["i"]
        if i < next_allowed.get(sid, 0):
            continue
        selected.append(event)
        # Signal bar i is only known at its close; the position starts at i+1 open
        # and expires at close of i+horizon. A new signal at i+horizon is allowed.
        next_allowed[sid] = i + horizon
    return selected


def outcome(seg: list[Bar], event: dict, horizon: int, direction: str):
    i = event["i"]
    if i + horizon >= len(seg) or i + 1 >= len(seg):
        return None
    entry = seg[i+1].open
    exit_price = seg[i+horizon].close
    delta = (exit_price-entry) * (1 if direction == "CALL" else -1)
    if abs(delta) <= 1e-12:
        label = "DRAW"
    else:
        label = "WIN" if delta > 0 else "LOSS"
    return {"outcome": label, "entry": entry, "exit": exit_price,
            "signal_ts": event["ts"], "settle_ts": seg[i+horizon].ts}


def split_name(global_index: int, train_end: int, val_end: int) -> str:
    return "TRAIN" if global_index < train_end else "VALIDATION" if global_index < val_end else "TEST"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("FICURA_JUMP_REPLICATION.md"))
    args = ap.parse_args()
    m1 = load_m1(args.data)
    if len(m1) < 100_000:
        raise SystemExit(f"Refusing short history: only {len(m1)} valid M1 bars")
    lines = [
        "# Fičura (2019) — frozen EUR/USD jump replication",
        "",
        f"Input: {args.data}; valid M1 BID rows={len(m1):,}; coverage {m1[0].ts.isoformat()} — {m1[-1].ts.isoformat()}.",
        "Frozen source parameters from Fičura (2019) Table 3; no tuning on this dataset.",
        "Primary causal entry: next bar open after completed jump bar; exit at close of signal bar + h.",
        "Source-close convention is not used as an executable result. BID-only prices are a proxy, not Pocket Option executable quotes.",
        f"Binary payout scenario: +{PAYOUT:.2f}u win, -1u loss, 0u draw; break-even decisive WR={100/(1+PAYOUT):.3f}%.",
        "Chronological split is 60/20/20 by bar count. Trades whose expiry crosses the next split boundary are purged.",
        "Non-overlap schedule is applied separately per expiry; exact inverse uses the same event timestamps.",
        "",
        "| TF | bars | segments | k | p | source h | events |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    tf_payload = {}
    for tf, (k, p, source_h) in SOURCE_PARAMS.items():
        bars = make_bars(m1, tf)
        segments = split_segments(bars, tf*60)
        total_returns = max(3, len(bars)-len(segments))
        events = make_events(segments, k, p, total_returns)
        tf_payload[tf] = (bars, segments, events, k, p, source_h)
        lines.append(f"| M{tf} | {len(bars):,} | {len(segments):,} | {k} | {p} | {source_h} | {len(events):,} |")
    lines += ["", "## Causal binary adaptations", ""]
    for tf, (bars, segments, events, k, p, source_h) in tf_payload.items():
        train_end = int(len(bars)*0.60)
        val_end = int(len(bars)*0.80)
        lines += [f"### M{tf} — frozen k={k}, p={p}; source h={source_h}", "",
                  "| Expiry (bars) | Split | Direction | N | W/L/D | WR | Wilson 95% | Net u |",
                  "|---:|---|---|---:|---:|---:|---:|---:|"]
        for h in BINARY_HORIZONS:
            chosen = nonoverlap(events, h)
            records = []
            for e in chosen:
                seg = segments[e["sid"]]
                result = outcome(seg, e, h, e["direction"])
                if result is None:
                    continue
                g = e["global"]
                split = split_name(g, train_end, val_end)
                # Purge outcomes that cross a chronological split boundary.
                exit_g = g + h
                if (split == "TRAIN" and exit_g >= train_end) or (split == "VALIDATION" and exit_g >= val_end):
                    continue
                records.append((split, e, result))
            for split in ("TRAIN", "VALIDATION", "TEST"):
                base = [x for x in records if x[0] == split]
                for direction_label, inverse in (("SOURCE", False), ("INVERSE", True)):
                    scored = []
                    for _, e, result in base:
                        direction = e["direction"]
                        if inverse:
                            direction = "PUT" if direction == "CALL" else "CALL"
                        # Re-score the same prices with the paired direction.
                        delta = (result["exit"]-result["entry"]) * (1 if direction == "CALL" else -1)
                        label = "DRAW" if abs(delta) <= 1e-12 else "WIN" if delta > 0 else "LOSS"
                        scored.append({"outcome": label})
                    s = binary_stats(scored, PAYOUT)
                    lines.append(f"| {h} | {split} | {direction_label} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {s['wr']:.2f}% | [{s['lo']:.2f}, {s['hi']:.2f}] | {s['net']:+.2f} |")
        lines.append("")
    lines += [
        "## Interpretation guardrails",
        "- This is an external replication/adaptation on modern Dukascopy history, not the paper's original 1999–2015 data.",
        "- M1/M5/M15/M30 selected parameters are copied from the paper's OOS table; they are not re-optimized here.",
        "- The paper's M15/M30 h=16 corresponds to 4h/8h holding periods. Binary expiries above are separate adaptations.",
        "- Wilson intervals assume independent outcomes and understate uncertainty under event clustering; use day-block bootstrap before drawing conclusions.",
        "- A BID-only historical feed cannot establish executable binary-option WR. Prospective quote-level validation remains mandatory.",
        "- TEST has been examined in previous Hydra research and is exploratory, not pristine independent evidence.",
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE={args.out} M1_ROWS={len(m1)} COVERAGE={m1[0].ts.isoformat()}..{m1[-1].ts.isoformat()}")


if __name__ == "__main__":
    main()
