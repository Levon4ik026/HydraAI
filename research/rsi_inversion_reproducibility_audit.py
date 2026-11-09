#!/usr/bin/env python3
"""Canonical reproducibility audit for the 2026-11-09 RSI inversion candidates.

Input: clean EURUSD M1 BID CSV (datetime_utc, open, high, low, close).
Signals are evaluated at completed M1 close; entry is next M1 open;
15-minute expiry is the close of the 15th entry candle.
No platform execution or payout simulation is performed here.
"""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

TRAIN_END = pd.Timestamp("2026-05-08T00:00:00Z")
TEST_START = pd.Timestamp("2026-08-06T00:00:00Z")
PIP = 0.0001
EXPECTED_SHA256 = "5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c"

def load(path: Path):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Unexpected dataset SHA256: {digest}")
    d = pd.read_csv(path)
    d["ts"] = pd.to_datetime(d["datetime_utc"], utc=True)
    d = d.sort_values("ts").reset_index(drop=True)
    d["segment"] = d["ts"].diff().dt.total_seconds().ne(60).cumsum()
    return d, digest

def features(d: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, g in d.groupby("segment", sort=False):
        x = g.copy()
        c = x.close.to_numpy(float)
        n = len(x)
        delta = np.diff(c, prepend=np.nan)
        gain = np.where(np.isfinite(delta), np.maximum(delta, 0.0), np.nan)
        loss = np.where(np.isfinite(delta), np.maximum(-delta, 0.0), np.nan)
        rsi = np.full(n, np.nan)
        if n > 14:
            ag = float(np.mean(gain[1:15]))
            al = float(np.mean(loss[1:15]))
            def value(a: float, b: float) -> float:
                if b == 0: return 100.0 if a > 0 else 50.0
                if a == 0: return 0.0
                return 100.0 - 100.0 / (1.0 + a / b)
            rsi[14] = value(ag, al)
            for i in range(15, n):
                ag = (ag * 13.0 + gain[i]) / 14.0
                al = (al * 13.0 + loss[i]) / 14.0
                rsi[i] = value(ag, al)
        alpha = 2.0 / 51.0
        ema = np.full(n, np.nan)
        if n:
            state = c[0]
            ema[0] = state
            for i in range(1, n):
                state = alpha * c[i] + (1.0 - alpha) * state
                ema[i] = state
        x["rsi14"] = rsi
        x["ema50"] = ema
        x["prev_rsi14"] = pd.Series(rsi, index=x.index).shift(1)
        x["cross_up70"] = (x.prev_rsi14 <= 70.0) & (x.rsi14 > 70.0)
        x["cross_down30"] = (x.prev_rsi14 >= 30.0) & (x.rsi14 < 30.0)
        x["high_minus_close_pips"] = (x.high - x.close) / PIP
        x["true_upper_wick_pips"] = (x.high - np.maximum(x.open, x.close)) / PIP
        candle_range = (x.high - x.low).replace(0, np.nan)
        x["true_upper_wick_range_fraction"] = (
            (x.high - np.maximum(x.open, x.close)) / candle_range)
        x["high_close_range_fraction"] = (x.high - x.close) / candle_range
        x["close_minus_ema50_pips"] = (x.close - x.ema50) / PIP
        parts.append(x)
    return pd.concat(parts).sort_index()

def build_ledger(f: pd.DataFrame, mask: pd.Series, direction: str) -> pd.DataFrame:
    """One-position schedule; signal i eligible if i >= prior expiry candle index."""
    rows = []
    for seg, g in f.groupby("segment", sort=False):
        ix = g.index.to_numpy()
        local_mask = mask.loc[ix].fillna(False).to_numpy(bool)
        last_expiry = -1
        for i in np.flatnonzero(local_mask):
            if i < last_expiry or i + 15 >= len(g):
                continue
            sig, entry_bar, expiry_bar = g.iloc[i], g.iloc[i+1], g.iloc[i+15]
            entry, exit_price = float(entry_bar.open), float(expiry_bar.close)
            if abs(exit_price - entry) < 1e-12:
                outcome = "DRAW"
            elif direction == "PUT":
                outcome = "WIN" if exit_price < entry else "LOSS"
            else:
                outcome = "WIN" if exit_price > entry else "LOSS"
            split = ("TRAIN" if sig.ts < TRAIN_END else
                     "VALIDATION" if sig.ts < TEST_START else "TEST")
            rows.append({
                "signal_time": sig.ts.isoformat(),
                "entry_time": entry_bar.ts.isoformat(),
                "expiry_time": expiry_bar.ts.isoformat(),
                "direction": direction, "entry": entry, "exit": exit_price,
                "outcome": outcome, "split": split, "segment": int(seg),
                "signal_close": float(sig.close), "rsi14": float(sig.rsi14),
                "ema50_distance_pips": float(sig.close_minus_ema50_pips),
                "high_minus_close_pips": float(sig.high_minus_close_pips),
                "true_upper_wick_pips": float(sig.true_upper_wick_pips),
                "true_upper_wick_range_fraction": (
                    float(sig.true_upper_wick_range_fraction)
                    if pd.notna(sig.true_upper_wick_range_fraction) else np.nan),
            })
            last_expiry = i + 15
    return pd.DataFrame(rows)

def summarize(ledger: pd.DataFrame, label: str) -> None:
    print(f"\n{label}")
    for split in ("TRAIN", "VALIDATION", "TEST"):
        q = ledger[ledger.split == split]
        w, l, dr = (int((q.outcome == z).sum()) for z in ("WIN", "LOSS", "DRAW"))
        decisive = w + l
        wr = 100.0 * w / decisive if decisive else float("nan")
        print(f"{split}: n={len(q)} W={w} L={l} D={dr} "
              f"decisive_WR={wr:.4f}% net92={w*0.92-l:.2f}u")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("research_output"))
    args = ap.parse_args()
    d, digest = load(args.data)
    f = features(d)
    print(f"rows={len(f)} segments={f.segment.nunique()} "
          f"first={f.ts.min().isoformat()} last={f.ts.max().isoformat()} sha256={digest}")
    bmask = f.cross_up70 & f.close_minus_ema50_pips.between(3.042, 5.692, inclusive="both")
    b = build_ledger(f, bmask, "PUT")
    summarize(b, "CANDIDATE B: RSI cross-up 70; close 3.042..5.692 pips above EMA50")
    raw = f[f.cross_down30]
    print("\nCANDIDATE A raw RSI-cross-down-30 diagnostics (before scheduling)")
    print(f"raw_crosses={len(raw)}")
    for col in ("high_minus_close_pips", "true_upper_wick_pips",
                "true_upper_wick_range_fraction", "high_close_range_fraction"):
        print(f"{col} <= 0.1: {int((raw[col] <= 0.1).sum())}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    target = args.out_dir / "rsi_candidate_b_trade_ledger.csv"
    b.to_csv(target, index=False)
    print(f"ledger={target}")

if __name__ == "__main__":
    main()
