#!/usr/bin/env python3
"""Frozen prospective PUT candidate; research-only, never opens trades.

Candidate fixed on 2026-11-07:
  BB(20, 2) upper-band re-entry + Williams %R(14) cross below -20,
  ADX(14) >= 15 and < 25,
  prior 3xM5 close-to-close momentum > 0,
  ATR(14)/close >= 0.0003596314.

Signal is evaluated after M5 close; entry is next M5 open; expiry is
that entry candle's close. Only complete UTC-aligned M5 candles and
same-segment consecutive candles are eligible. Payout is fixed at 92%.
The threshold is frozen; do not recalibrate it on prospective data.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from reproduce_m5_bb_williams_adx import (  # noqa: E402
    PAYOUT, Bar, indicators, load_m1, make_m5, summary,
)

ATR_RATIO_FLOOR = 0.0003596314
ADX_MIN = 15.0
ADX_MAX_EXCLUSIVE = 25.0
DEFAULT_FORWARD_START = "2026-11-05T16:10:00+00:00"


def wilder_atr(bars: list[Bar], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    if len(bars) < period:
        return out
    tr = []
    for i, bar in enumerate(bars):
        if i == 0:
            tr.append(bar.high - bar.low)
        else:
            prev = bars[i - 1]
            tr.append(max(bar.high - bar.low, abs(bar.high - prev.close),
                          abs(bar.low - prev.close)))
    state = sum(tr[:period]) / period
    out[period - 1] = state
    for i in range(period, len(bars)):
        state = (state * (period - 1) + tr[i]) / period
        out[i] = state
    return out


def parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone, preferably Z.")
    return dt.astimezone(timezone.utc)


def build_candidate(segments: list[list[Bar]]) -> list[dict]:
    trades: list[dict] = []
    for segment_id, bars in enumerate(segments):
        base = indicators(bars)
        atr = wilder_atr(bars)
        for i in range(1, len(bars) - 1):
            cur, prev = bars[i], bars[i - 1]
            b, p = base[i], base[i - 1]
            if i < 3 or atr[i] is None or b["adx"] is None:
                continue
            required = ("upper", "willr")
            if any(b[k] is None or p[k] is None for k in required):
                continue
            momentum3 = cur.close - bars[i - 3].close
            atr_ratio = atr[i] / cur.close
            signal = (
                prev.close > p["upper"] and cur.close < b["upper"]
                and p["willr"] >= -20.0 and b["willr"] < -20.0
                and b["adx"] >= ADX_MIN and b["adx"] < ADX_MAX_EXCLUSIVE
                and momentum3 > 0.0 and atr_ratio >= ATR_RATIO_FLOOR
            )
            if not signal:
                continue
            nxt = bars[i + 1]
            if nxt.timestamp - cur.timestamp != timedelta(minutes=5):
                continue
            delta = nxt.close - nxt.open
            outcome = "DRAW" if abs(delta) < 1e-12 else "WIN" if delta < 0 else "LOSS"
            trades.append({
                "signal_time": cur.timestamp,
                "entry_time": nxt.timestamp,
                "settlement_time": nxt.timestamp + timedelta(minutes=5),
                "segment_id": segment_id,
                "outcome": outcome,
                "profit": 0.0 if outcome == "DRAW" else PAYOUT if outcome == "WIN" else -1.0,
                "adx": b["adx"],
                "atr_ratio": atr_ratio,
                "momentum3": momentum3,
            })
            # Signals are already evaluated on each candle close; expiry is
            # entry candle close, so the next signal may be evaluated there.
    return trades


def summarize(label: str, trades: list[dict]) -> None:
    s = summary(trades)
    print(f"{label}: trades={s['trades']} decisive={s['decisive']} "
          f"W/L/D={s['wins']}/{s['losses']}/{s['draws']} "
          f"WR={s['win_rate']:.2f}% CI95={s['wilson_95_pct']} "
          f"net={s['net_92']:.2f} maxDD={s['max_drawdown_units']:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True,
                    help="M1 CSV with datetime_utc,open,high,low,close")
    ap.add_argument("--forward-start", default=DEFAULT_FORWARD_START,
                    help="UTC timestamp; all signals before this are historical only")
    ap.add_argument("--out", type=Path, default=ROOT / "research" / "frozen_put_candidate_trades.csv")
    args = ap.parse_args()

    forward_start = parse_utc(args.forward_start)
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    all_trades = build_candidate(segments)
    historical = [t for t in all_trades if t["signal_time"] < forward_start]
    forward = [t for t in all_trades if t["signal_time"] >= forward_start]

    print("FROZEN PUT CANDIDATE — RESEARCH ONLY — payout 92%")
    print(f"Fixed ATR/close floor={ATR_RATIO_FLOOR:.10f}; ADX=[{ADX_MIN},{ADX_MAX_EXCLUSIVE}); momentum3>0")
    print(f"M1 rows={len(m1)}; complete M5 bars={sum(map(len, segments))}; segments={len(segments)}")
    print(f"Observed M1 range={m1[0].timestamp.isoformat()} .. {m1[-1].timestamp.isoformat()}")
    print(f"Forward evaluation begins at {forward_start.isoformat()}")
    summarize("HISTORICAL (not validation)", historical)
    summarize("FORWARD (valid only if timestamps are genuinely newly collected)", forward)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["signal_time", "entry_time", "settlement_time", "segment_id",
              "outcome", "profit", "adx", "atr_ratio", "momentum3"]
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for trade in all_trades:
            row = dict(trade)
            for k in ("signal_time", "entry_time", "settlement_time"):
                row[k] = row[k].isoformat()
            writer.writerow(row)
    print(f"Trade ledger written: {args.out}")
    print("DECISION RULE: do not alter thresholds after forward collection begins. "
          "Report every eligible trade, including losses and draws. No production use.")


if __name__ == "__main__":
    main()
