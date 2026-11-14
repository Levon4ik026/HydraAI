#!/usr/bin/env python3
"""Reproduce the RSI extreme-follow inversion and its upper-wick CALL subset.

Signals are generated from completed M1 candles. A single shared position lock
is applied across BOTH RSI threshold-cross directions before any feature filter:
- RSI crosses above 70: original CALL
- RSI crosses below 30: original PUT
The inverted direction is the exact opposite on the same entry/expiry prices.

Entry: next M1 open. Expiry: close of signal index + 15.
A new raw RSI signal is eligible at the prior expiry candle index or later.
"""
import argparse, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED_SHA256 = "5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c"
PIP = 0.0001
TRAIN_END = pd.Timestamp("2026-05-08T00:00:00Z")
TEST_START = pd.Timestamp("2026-08-06T00:00:00Z")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("research_output/rsi_shared_schedule_ledger.csv"))
    args = ap.parse_args()
    raw = args.data.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Dataset SHA256 mismatch: {digest}")
    d = pd.read_csv(args.data)
    d["ts"] = pd.to_datetime(d["datetime_utc"], utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    d["segment"] = d.ts.diff().dt.total_seconds().ne(60).cumsum()

    chunks = []
    for _, g in d.groupby("segment", sort=False):
        x = g.copy()
        c = x.close.to_numpy(float)
        n = len(x)
        delta = np.diff(c, prepend=np.nan)
        gain = np.where(np.isfinite(delta), np.maximum(delta, 0.0), np.nan)
        loss = np.where(np.isfinite(delta), np.maximum(-delta, 0.0), np.nan)
        rsi = np.full(n, np.nan)
        if n > 14:
            avg_gain = float(np.mean(gain[1:15]))
            avg_loss = float(np.mean(loss[1:15]))
            def rsi_value(a, b):
                if b == 0:
                    return 100.0 if a > 0 else 50.0
                if a == 0:
                    return 0.0
                return 100.0 - 100.0 / (1.0 + a / b)
            rsi[14] = rsi_value(avg_gain, avg_loss)
            for i in range(15, n):
                avg_gain = (avg_gain * 13.0 + gain[i]) / 14.0
                avg_loss = (avg_loss * 13.0 + loss[i]) / 14.0
                rsi[i] = rsi_value(avg_gain, avg_loss)
        x["rsi14"] = rsi
        x["prev_rsi14"] = pd.Series(rsi, index=x.index).shift(1)
        x["cross_up70"] = (x.prev_rsi14 <= 70.0) & (x.rsi14 > 70.0)
        x["cross_down30"] = (x.prev_rsi14 >= 30.0) & (x.rsi14 < 30.0)
        # Geometric upper wick, not the high-to-close distance.
        x["upper_wick_pips"] = (x.high - np.maximum(x.open, x.close)) / PIP
        chunks.append(x)
    f = pd.concat(chunks).sort_index()

    accepted = []
    for seg, g in f.groupby("segment", sort=False):
        lock_until = -1
        for i in range(len(g)):
            s = g.iloc[i]
            up, down = bool(s.cross_up70), bool(s.cross_down30)
            if not (up or down) or i < lock_until or i + 15 >= len(g):
                continue
            entry, expiry = g.iloc[i + 1], g.iloc[i + 15]
            split = ("TRAIN" if s.ts < TRAIN_END else
                     "VALIDATION" if s.ts < TEST_START else "TEST")
            original_side = "CALL" if up else "PUT"
            original_win = ((expiry.close > entry.open) if up else
                            (expiry.close < entry.open))
            original_loss = ((expiry.close < entry.open) if up else
                             (expiry.close > entry.open))
            outcome = "WIN" if original_win else "LOSS" if original_loss else "DRAW"
            accepted.append({
                "signal_time": s.ts.isoformat(),
                "entry_time": entry.ts.isoformat(),
                "expiry_time": expiry.ts.isoformat(),
                "split": split, "segment": int(seg),
                "original_side": original_side,
                "original_outcome": outcome,
                "inverse_side": "PUT" if up else "CALL",
                "inverse_outcome": ("LOSS" if outcome == "WIN" else
                                    "WIN" if outcome == "LOSS" else "DRAW"),
                "upper_wick_pips": float(s.upper_wick_pips),
                "rsi14": float(s.rsi14),
                "entry_open": float(entry.open),
                "expiry_close": float(expiry.close),
                "is_candidate_a": bool(down and s.upper_wick_pips <= 0.1),
            })
            lock_until = i + 15

    ledger = pd.DataFrame(accepted)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(args.out, index=False)
    print(f"dataset_sha256={digest}")
    print(f"rows={len(f)} segments={f.segment.nunique()} shared_scheduled_signals={len(ledger)}")
    print("All signals share one lockout; candidate filters are applied AFTER scheduling.")
    for label, q in (("RSI_ALL", ledger), ("CANDIDATE_A", ledger[ledger.is_candidate_a])):
        for side, col in (("ORIGINAL", "original_outcome"), ("INVERSE", "inverse_outcome")):
            print(f"\\n{label} — {side}")
            for split in ("TRAIN", "VALIDATION", "TEST"):
                z = q[q.split == split]
                w = int((z[col] == "WIN").sum())
                l = int((z[col] == "LOSS").sum())
                dr = int((z[col] == "DRAW").sum())
                n = w + l
                wr = 100.0 * w / n if n else float("nan")
                print(f"{split}: trades={len(z)} W={w} L={l} D={dr} "
                      f"decisive_WR={wr:.4f}% net92={0.92*w-l:.2f}u")
    print(f"ledger={args.out}")

if __name__ == "__main__":
    main()
