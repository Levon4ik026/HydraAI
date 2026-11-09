#!/usr/bin/env python3
"""Matched direct/inverse screen for EURUSD M1; research only."""
import argparse, hashlib
import numpy as np
import pandas as pd

EXPECTED_SHA256 = "5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c"
HORIZON = 15
PAYOUT = 0.92

def rsi_wilder(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).to_numpy()
    loss = (-delta.clip(upper=0)).to_numpy()
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    avg_gain, avg_loss = gain[1:n+1].mean(), loss[1:n+1].mean()
    out[n] = 100.0 if avg_loss == 0 and avg_gain > 0 else (0.0 if avg_gain == 0 else 100-100/(1+avg_gain/avg_loss))
    for i in range(n+1, len(close)):
        avg_gain = (avg_gain*(n-1)+gain[i])/n
        avg_loss = (avg_loss*(n-1)+loss[i])/n
        out[i] = 100.0 if avg_loss == 0 and avg_gain > 0 else (0.0 if avg_gain == 0 else 100-100/(1+avg_gain/avg_loss))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="clean M1 CSV")
    ap.add_argument("--payout", type=float, default=PAYOUT)
    args = ap.parse_args()
    raw_bytes = open(args.csv, "rb").read()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"Dataset SHA mismatch: {digest}")
    d = pd.read_csv(args.csv, parse_dates=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)
    d["segment"] = (d.datetime_utc.diff().dt.total_seconds().fillna(60) != 60).cumsum()
    chunks = []
    for _, g in d.groupby("segment", sort=False):
        x = g.copy()
        c = x.close
        x["ema8"] = c.ewm(span=8, adjust=False, min_periods=8).mean()
        x["ema21"] = c.ewm(span=21, adjust=False, min_periods=21).mean()
        x["prior_ema8"] = x.ema8.shift()
        x["prior_ema21"] = x.ema21.shift()
        x["prior_high20"] = x.high.shift().rolling(20, min_periods=20).max()
        x["prior_low20"] = x.low.shift().rolling(20, min_periods=20).min()
        x["up3"] = ((c > x.open) & (c.shift(1) > x.open.shift(1)) & (c.shift(2) > x.open.shift(2)))
        x["dn3"] = ((c < x.open) & (c.shift(1) < x.open.shift(1)) & (c.shift(2) < x.open.shift(2)))
        x["ret5"] = c / c.shift(5) - 1
        x["rsi14"] = rsi_wilder(c)
        x["rsi_prev"] = x.rsi14.shift()
        chunks.append(x)
    d = pd.concat(chunks).sort_index().reset_index(drop=True)
    rules = {
        "EMA8_21_crossover": np.where((d.prior_ema8 <= d.prior_ema21) & (d.ema8 > d.ema21), 1,
            np.where((d.prior_ema8 >= d.prior_ema21) & (d.ema8 < d.ema21), -1, 0)),
        "20bar_breakout_follow": np.where(d.close > d.prior_high20, 1, np.where(d.close < d.prior_low20, -1, 0)),
        "three_candle_momentum_follow": np.where(d.up3, 1, np.where(d.dn3, -1, 0)),
        "five_min_impulse_003pct": np.where(d.ret5 >= .0003, 1, np.where(d.ret5 <= -.0003, -1, 0)),
        "RSI_extreme_cross_follow": np.where((d.rsi_prev <= 70) & (d.rsi14 > 70), 1,
            np.where((d.rsi_prev >= 30) & (d.rsi14 < 30), -1, 0)),
    }
    ts, op, cl, seg = d.datetime_utc, d.open.to_numpy(), d.close.to_numpy(), d.segment.to_numpy()
    train_end, test_start = pd.Timestamp("2026-05-08", tz="UTC"), pd.Timestamp("2026-08-06", tz="UTC")
    for name, signals in rules.items():
        accepted, next_allowed = [], -1
        for i, side in enumerate(signals):
            if side and i >= next_allowed and i+HORIZON < len(d) and seg[i] == seg[i+1] == seg[i+HORIZON]:
                accepted.append((i, int(side)))
                next_allowed = i + HORIZON
        records = []
        for i, side in accepted:
            entry, expiry = op[i+1], cl[i+HORIZON]
            outcome = 1 if (expiry > entry if side > 0 else expiry < entry) else (-1 if (expiry < entry if side > 0 else expiry > entry) else 0)
            records.append((i, outcome))
        print("\\n" + name)
        for label, keep in [
            ("TRAIN", lambda t: t < train_end),
            ("VALIDATION", lambda t: train_end <= t < test_start),
            ("TEST", lambda t: t >= test_start),
        ]:
            vals = [(-o if o else 0) for i, o in records if keep(ts.iloc[i])]
            w, l, draw = vals.count(1), vals.count(-1), vals.count(0)
            n = w+l
            wr = 100*w/n if n else float("nan")
            net = args.payout*w-l
            print(f"{label}: N={len(vals)} inverse W/L/D={w}/{l}/{draw} WR={wr:.2f}% net={net:.2f}u")
        for month in ("2026-08", "2026-09", "2026-10", "2026-11"):
            vals = [(-o if o else 0) for i, o in records if ts.iloc[i].strftime("%Y-%m") == month and ts.iloc[i] >= test_start]
            if vals:
                w, l, draw = vals.count(1), vals.count(-1), vals.count(0)
                n = w+l
                print(f"{month}: N={len(vals)} W/L/D={w}/{l}/{draw} WR={100*w/n:.2f}% net={args.payout*w-l:.2f}u")
if __name__ == "__main__":
    main()
