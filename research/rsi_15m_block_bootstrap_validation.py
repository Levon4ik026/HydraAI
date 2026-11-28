#!/usr/bin/env python3
"""Prospective-style statistical stress audit for the frozen RSI inverse, research only."""
import argparse, hashlib
import numpy as np
import pandas as pd

EXPECTED_SHA256 = "5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c"
PAYOUT = 0.92
HORIZON = 15
SEED = 20261109
BOOTSTRAPS = 30000
BLOCK_LENGTHS = (3, 7, 14, 21)

def wilder_rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).to_numpy()
    loss = (-delta.clip(upper=0)).to_numpy()
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    ag, al = gain[1:n+1].mean(), loss[1:n+1].mean()
    out[n] = 100.0 if al == 0 and ag > 0 else (0.0 if ag == 0 else 100.0 - 100.0/(1.0 + ag/al))
    for i in range(n+1, len(close)):
        ag = (ag*(n-1) + gain[i])/n
        al = (al*(n-1) + loss[i])/n
        out[i] = 100.0 if al == 0 and ag > 0 else (0.0 if ag == 0 else 100.0 - 100.0/(1.0 + ag/al))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    raw = open(args.csv, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"SHA256 mismatch: {digest}")
    d = pd.read_csv(args.csv, parse_dates=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)
    d["segment"] = (d.datetime_utc.diff().dt.total_seconds().fillna(60) != 60).cumsum()
    parts = []
    for _, g in d.groupby("segment", sort=False):
        x = g.copy()
        x["rsi"] = wilder_rsi(x.close)
        x["prev_rsi"] = x.rsi.shift()
        parts.append(x)
    d = pd.concat(parts).sort_index().reset_index(drop=True)
    signal = np.where((d.prev_rsi <= 70) & (d.rsi > 70), 1,
             np.where((d.prev_rsi >= 30) & (d.rsi < 30), -1, 0))
    ts = d.datetime_utc
    op, cl, seg = d.open.to_numpy(), d.close.to_numpy(), d.segment.to_numpy()
    accepted, next_allowed = [], -1
    for i, side in enumerate(signal):
        if side and i >= next_allowed and i+HORIZON < len(d) and seg[i] == seg[i+1] == seg[i+HORIZON]:
            direct = 1 if (cl[i+HORIZON] > op[i+1] if side > 0 else cl[i+HORIZON] < op[i+1]) else (
                -1 if (cl[i+HORIZON] < op[i+1] if side > 0 else cl[i+HORIZON] > op[i+1]) else 0)
            accepted.append((i, int(side), direct))
            next_allowed = i + HORIZON

    train_end = pd.Timestamp("2026-05-08", tz="UTC")
    test_start = pd.Timestamp("2026-08-06", tz="UTC")
    rows = []
    for i, side, direct in accepted:
        inverse = -direct if direct else 0
        rows.append((ts.iloc[i], direct, inverse, op[i+1], cl[i+HORIZON]))
    z = pd.DataFrame(rows, columns=["signal_time", "direct", "inverse", "entry_open", "expiry_close"])
    z["split"] = np.where(z.signal_time < train_end, "TRAIN",
                  np.where(z.signal_time < test_start, "VALIDATION", "TEST"))
    print(f"sha256={digest}; rows={len(d)}; segments={d.segment.nunique()}; accepted={len(z)}")
    for split in ("TRAIN", "VALIDATION", "TEST"):
        q = z[z.split == split]
        w, l, dr = int((q.inverse == 1).sum()), int((q.inverse == -1).sum()), int((q.inverse == 0).sum())
        print(f"{split}: N={len(q)} inverse W/L/D={w}/{l}/{dr} WR={100*w/(w+l):.4f}% net92={PAYOUT*w-l:.2f}u")
    # Exact matched cohort invariant.
    assert (z.direct == -z.inverse).all()
    assert len(z) == z.signal_time.nunique()
    q = z[z.split == "TEST"].copy()
    q["date"] = q.signal_time.dt.floor("D")
    daily = q.groupby("date").inverse.agg(
        wins=lambda s: int((s == 1).sum()),
        losses=lambda s: int((s == -1).sum()),
        draws=lambda s: int((s == 0).sum())
    ).asfreq("D", fill_value=0)
    a = daily[["wins", "losses", "draws"]].to_numpy()
    ow, ol, od = a.sum(axis=0)
    print(f"TEST observed: W/L/D={ow}/{ol}/{od}; decisive_WR={100*ow/(ow+ol):.4f}%; net92={PAYOUT*ow-ol:.2f}u; calendar_days={len(a)}")
    for block in BLOCK_LENGTHS:
        rng = np.random.default_rng(SEED + block)
        totals = np.empty((BOOTSTRAPS, 3), dtype=float)
        for b in range(BOOTSTRAPS):
            idx = []
            while len(idx) < len(a):
                start = int(rng.integers(0, len(a)))
                idx.extend((start+j) % len(a) for j in range(block))
            totals[b] = a[np.asarray(idx[:len(a)])].sum(axis=0)
        w, l, _ = totals.T
        wr = w/(w+l)
        net = PAYOUT*w-l
        print(f"BLOCK={block}d B={BOOTSTRAPS} WR95=[{np.quantile(wr,.025):.5f},{np.quantile(wr,.975):.5f}] "
              f"net95=[{np.quantile(net,.025):.2f},{np.quantile(net,.975):.2f}] "
              f"P(net<=0)={np.mean(net<=0):.5f}")
    print("Note: circular moving-block bootstrap of daily counts; exploratory, unadjusted for candidate/horizon selection.")

if __name__ == "__main__":
    main()
