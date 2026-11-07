#!/usr/bin/env python3
"""Exploratory PUT-only strategy screen on committed EURUSD M1 history.

Research-only: 92% payout, signal after M5 close, entry next M5 open,
settlement at that M5 close. No production integration.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from reproduce_m5_bb_williams_adx import (  # noqa: E402
    DATA_PATH, PAYOUT, Bar, indicators, load_m1, make_m5, summary,
)


def ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    state = sum(values[:period]) / period
    out[period - 1] = state
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        state += alpha * (values[i] - state)
        out[i] = state
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, len(values))]
    ag, al = sum(gains[:period]) / period, sum(losses[:period]) / period
    def value(g: float, l: float) -> float:
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + g / l)
    out[period] = value(ag, al)
    for i in range(period + 1, len(values)):
        ag = (ag * (period - 1) + gains[i - 1]) / period
        al = (al * (period - 1) + losses[i - 1]) / period
        out[i] = value(ag, al)
    return out


def stochastic(bars: list[Bar], period: int = 14) -> tuple[list, list]:
    k: list[float | None] = [None] * len(bars)
    d: list[float | None] = [None] * len(bars)
    for i in range(period - 1, len(bars)):
        hi = max(x.high for x in bars[i - period + 1:i + 1])
        lo = min(x.low for x in bars[i - period + 1:i + 1])
        k[i] = 50.0 if hi == lo else 100.0 * (bars[i].close - lo) / (hi - lo)
        if i >= period + 1 and all(x is not None for x in k[i - 2:i + 1]):
            d[i] = sum(k[i - 2:i + 1]) / 3.0
    return k, d


def cci(bars: list[Bar], period: int = 20) -> list[float | None]:
    tp = [(b.high + b.low + b.close) / 3.0 for b in bars]
    out: list[float | None] = [None] * len(bars)
    for i in range(period - 1, len(bars)):
        w = tp[i - period + 1:i + 1]
        mean = sum(w) / period
        dev = sum(abs(x - mean) for x in w) / period
        out[i] = 0.0 if dev == 0 else (tp[i] - mean) / (0.015 * dev)
    return out


def macd_hist(values: list[float]) -> list[float | None]:
    fast, slow = ema(values, 12), ema(values, 26)
    line: list[float | None] = [None] * len(values)
    for i in range(len(values)):
        if fast[i] is not None and slow[i] is not None:
            line[i] = fast[i] - slow[i]
    valid = [x for x in line if x is not None]
    signal_valid = ema(valid, 9)
    signal: list[float | None] = [None] * len(values)
    j = 0
    for i, x in enumerate(line):
        if x is not None:
            signal[i] = signal_valid[j]
            j += 1
    return [None if line[i] is None or signal[i] is None else line[i] - signal[i]
            for i in range(len(values))]


def atr(bars: list[Bar], period: int = 14) -> list[float | None]:
    tr: list[float] = []
    for i, b in enumerate(bars):
        if i == 0:
            tr.append(b.high - b.low)
        else:
            prev = bars[i - 1]
            tr.append(max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close)))
    out: list[float | None] = [None] * len(bars)
    if len(bars) >= period:
        state = sum(tr[:period]) / period
        out[period - 1] = state
        for i in range(period, len(bars)):
            state = (state * (period - 1) + tr[i]) / period
            out[i] = state
    return out


def make_features(bars: list[Bar]) -> dict:
    close = [b.close for b in bars]
    base = indicators(bars)
    e20, e50, e100 = ema(close, 20), ema(close, 50), ema(close, 100)
    r14 = rsi(close)
    sk, sd = stochastic(bars)
    ch = cci(bars)
    mh = macd_hist(close)
    at = atr(bars)
    return {"base": base, "ema20": e20, "ema50": e50, "ema100": e100,
            "rsi": r14, "stoch_k": sk, "stoch_d": sd, "cci": ch,
            "macd_hist": mh, "atr": at}


def signal_at(name: str, i: int, bars: list[Bar], f: dict) -> bool:
    if i < 1:
        return False
    b, p = f["base"][i], f["base"][i - 1]
    c, prev = bars[i], bars[i - 1]
    e20, e50, e100 = f["ema20"], f["ema50"], f["ema100"]
    rv, sk, sd = f["rsi"], f["stoch_k"], f["stoch_d"]
    cc, mh, at = f["cci"], f["macd_hist"], f["atr"]
    name, _, setting = name.partition(":")
    if name == "BB_WILLR":
        return (p["upper"] is not None and b["upper"] is not None and
                f["base"][i - 1]["willr"] is not None and f["base"][i]["willr"] is not None and
                prev.close > p["upper"] and c.close < b["upper"] and
                f["base"][i - 1]["willr"] >= -20 and f["base"][i]["willr"] < -20 and
                (setting == "any" or (b["adx"] is not None and b["adx"] >= float(setting))))
    if name == "RSI_FADE":
        level = float(setting)
        return (rv[i - 1] is not None and rv[i] is not None and
                rv[i - 1] >= level and rv[i] < level and
                e20[i] is not None and c.close < e20[i])
    if name == "STOCH_TREND":
        return (sk[i - 1] is not None and sk[i] is not None and
                sd[i - 1] is not None and sd[i] is not None and
                sk[i - 1] >= 80 and sk[i - 1] >= sd[i - 1] and sk[i] < sd[i] and
                e50[i] is not None and c.close < e50[i])
    if name == "EMA_PULLBACK":
        return (e20[i - 1] is not None and e20[i] is not None and
                e50[i] is not None and rv[i] is not None and
                prev.close >= e20[i - 1] and c.close < e20[i] and
                e20[i] < e50[i] and rv[i] < 50)
    if name == "DONCHIAN_BREAK":
        lookback = int(setting)
        if i < lookback or b["plus_di"] is None or b["minus_di"] is None or b["adx"] is None:
            return False
        floor = min(x.low for x in bars[i - lookback:i])
        return c.close < floor and b["minus_di"] > b["plus_di"] and b["adx"] >= 15
    if name == "MACD_ZERO":
        return (mh[i - 1] is not None and mh[i] is not None and
                mh[i - 1] >= 0 and mh[i] < 0 and e50[i] is not None and c.close < e50[i])
    if name == "CCI_FADE":
        return (cc[i - 1] is not None and cc[i] is not None and
                cc[i - 1] >= 100 and cc[i] < 100 and e50[i] is not None and c.close < e50[i])
    if name == "BEAR_ENGULF":
        return (e50[i] is not None and e50[i - 1] is not None and
                b["adx"] is not None and b["adx"] >= float(setting) and
                c.close < c.open and prev.close > prev.open and
                c.open >= prev.close and c.close <= prev.open and
                e50[i] < e50[i - 1] and c.close < e50[i])
    if name == "ATR_EXPANSION":
        lookback = int(setting)
        if i < lookback or at[i] is None or e50[i] is None:
            return False
        prior_low = min(x.low for x in bars[i - lookback:i])
        return (c.close < prior_low and c.close < e50[i] and
                c.close < c.open and (c.high - c.low) > at[i] * 1.2)
    return False


def candidates() -> list[str]:
    out = []
    out += [f"BB_WILLR:{x}" for x in ("any", "15", "20")]
    out += [f"RSI_FADE:{x}" for x in ("65", "70", "75")]
    out += ["STOCH_TREND:80", "EMA_PULLBACK:20"]
    out += [f"DONCHIAN_BREAK:{x}" for x in ("10", "20", "40")]
    out += ["MACD_ZERO:12_26_9", "CCI_FADE:100"]
    out += [f"BEAR_ENGULF:{x}" for x in ("15", "20", "25")]
    out += [f"ATR_EXPANSION:{x}" for x in ("10", "20")]
    return out


def build_candidate_trades(segments: list[list[Bar]], candidate: str) -> list[dict]:
    rows = []
    for sid, bars in enumerate(segments):
        f = make_features(bars)
        for i, bar in enumerate(bars):
            rows.append({"bar": bar, "segment": sid,
                         "signal": signal_at(candidate, i, bars, f),
                         "adx": f["base"][i]["adx"],
                         "plus_di": f["base"][i]["plus_di"],
                         "minus_di": f["base"][i]["minus_di"],
                         "ema20": f["ema20"][i], "ema50": f["ema50"][i],
                         "ema50_slope3": (f["ema50"][i] - f["ema50"][i - 3]
                                          if i >= 3 and f["ema50"][i] is not None and f["ema50"][i - 3] is not None else None),
                         "rsi": f["rsi"][i], "momentum3": (
                             bar.close - bars[i - 3].close if i >= 3 else None)})
    trades = []
    i = 0
    while i < len(rows) - 1:
        r = rows[i]
        n = rows[i + 1]
        if not r["signal"]:
            i += 1
            continue
        if n["segment"] != r["segment"] or n["bar"].timestamp - r["bar"].timestamp != timedelta(minutes=5):
            i += 1
            continue
        delta = n["bar"].close - n["bar"].open
        outcome = "DRAW" if abs(delta) < 1e-12 else "WIN" if delta < 0 else "LOSS"
        trades.append({"outcome": outcome, "profit": 0.0 if outcome == "DRAW" else PAYOUT if outcome == "WIN" else -1.0,
                       "signal_time": r["bar"].timestamp, "entry_time": n["bar"].timestamp,
                       "adx": r["adx"], "plus_di": r["plus_di"], "minus_di": r["minus_di"],
                       "ema20": r["ema20"], "ema50": r["ema50"], "ema50_slope3": r["ema50_slope3"],
                       "rsi": r["rsi"], "momentum3": r["momentum3"],
                       "settlement_time": n["bar"].timestamp + timedelta(minutes=5)})
        i += 1
    return trades


def concise(trades: list[dict]) -> dict:
    s = summary(trades)
    return {k: s[k] for k in ("trades", "wins", "losses", "draws", "decisive", "win_rate",
                               "wilson_95_pct", "net_92", "max_drawdown_units")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_PATH)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    m1 = load_m1(args.data)
    segments = make_m5(m1)
    total = sum(map(len, segments))
    boundary = sorted(b.timestamp for seg in segments for b in seg)[int(total * .70)]
    print(f"PUT-ONLY EXPLORATORY SCREEN | payout={PAYOUT:.2f} | M1={len(m1)} | M5={total} | segments={len(segments)}")
    print(f"Range={min(seg[0].timestamp for seg in segments)} .. {max(seg[-1].timestamp for seg in segments)} | 70/30 boundary={boundary}")
    results = []
    for candidate in candidates():
        trades = build_candidate_trades(segments, candidate)
        train = [t for t in trades if t["settlement_time"] < boundary]
        test = [t for t in trades if t["settlement_time"] >= boundary]
        results.append((candidate, train, test))
    eligible = [x for x in results if concise(x[1])["decisive"] >= 25]
    eligible.sort(key=lambda x: (concise(x[1])["net_92"], concise(x[1])["win_rate"]), reverse=True)
    print(f"Candidates={len(results)} | candidates with >=25 decisive train trades={len(eligible)}")
    print("RANKED BY TRAIN NET ONLY (holdout is displayed, not used for ranking)")
    for rank, (name, train, test) in enumerate(eligible[:args.top], 1):
        print(f"{rank:02d}. {name} | TRAIN {concise(train)} | HOLDOUT {concise(test)}")
        weekly: dict[str, list[dict]] = defaultdict(list)
        for t in test:
            week = (t["signal_time"] - timedelta(days=t["signal_time"].weekday())).strftime("%Y-%m-%d")
            weekly[week].append(t)
        if weekly:
            print("    HOLDOUT WEEKS " + " | ".join(f"{w}: {concise(v)}" for w, v in sorted(weekly.items())))
    # Diagnostic-only regime breakdowns for the leading structurally different candidates.
    print("CONTEXT DIAGNOSTICS (descriptive, small groups; not used to select candidates)")
    for target in ("STOCH_TREND:80", "EMA_PULLBACK:20", "ATR_EXPANSION:20", "DONCHIAN_BREAK:40"):
        trades = next((x[1] + x[2] for x in results if x[0] == target), [])
        if not trades:
            continue
        print(f"  {target}")
        dimensions = {
            "DMI": lambda t: ("BEARISH" if t["minus_di"] is not None and t["plus_di"] is not None and t["minus_di"] > t["plus_di"] else "BULLISH_OR_NA"),
            "MOM3": lambda t: ("DOWN" if t["momentum3"] is not None and t["momentum3"] < 0 else "UP_OR_FLAT"),
            "ADX": lambda t: ("<15" if t["adx"] is not None and t["adx"] < 15 else "15-25" if t["adx"] is not None and t["adx"] < 25 else ">=25" if t["adx"] is not None else "NA"),
            "EMA50_SLOPE": lambda t: ("DOWN" if t["ema50_slope3"] is not None and t["ema50_slope3"] < 0 else "UP_OR_NA"),
            "RSI": lambda t: ("<40" if t["rsi"] is not None and t["rsi"] < 40 else "40-50" if t["rsi"] is not None and t["rsi"] < 50 else ">=50_OR_NA"),
        }
        for dim, classify in dimensions.items():
            groups = defaultdict(list)
            for trade in trades:
                groups[classify(trade)].append(trade)
            print("    " + dim + ": " + " | ".join(f"{key}={concise(val)}" for key, val in sorted(groups.items())))
    # One-factor-at-a-time diagnostics for the EMA pullback candidate. These
    # are descriptive probes, not an invitation to optimize against this holdout.
    base_ema = next((x[1] + x[2] for x in results if x[0] == "EMA_PULLBACK:20"), [])
    if base_ema:
        filters = {
            "base": lambda t: True,
            "bearish_DMI": lambda t: t["minus_di"] is not None and t["plus_di"] is not None and t["minus_di"] > t["plus_di"],
            "ADX>=15": lambda t: t["adx"] is not None and t["adx"] >= 15,
            "ADX>=20": lambda t: t["adx"] is not None and t["adx"] >= 20,
            "MOM3_down": lambda t: t["momentum3"] is not None and t["momentum3"] < 0,
            "EMA50_slope_down": lambda t: t["ema50_slope3"] is not None and t["ema50_slope3"] < 0,
            "RSI<45": lambda t: t["rsi"] is not None and t["rsi"] < 45,
            "bearish_DMI+MOM3_down": lambda t: t["minus_di"] is not None and t["plus_di"] is not None and t["minus_di"] > t["plus_di"] and t["momentum3"] is not None and t["momentum3"] < 0,
        }
        print("EMA_PULLBACK ONE-FACTOR CONTEXT PROBES")
        for label, predicate in filters.items():
            selected = [t for t in base_ema if predicate(t)]
            tr = [t for t in selected if t["settlement_time"] < boundary]
            ho = [t for t in selected if t["settlement_time"] >= boundary]
            print(f"  {label}: TRAIN={concise(tr)} | HOLDOUT={concise(ho)}")
        print("EMA_PULLBACK REGIME STABILITY BY PERIOD")
        for period, subset in (("TRAIN", [t for t in base_ema if t["settlement_time"] < boundary]),
                               ("HOLDOUT", [t for t in base_ema if t["settlement_time"] >= boundary])):
            print(f"  {period}")
            groups = defaultdict(list)
            for t in subset:
                dmi = "BEARISH_DMI" if t["minus_di"] is not None and t["plus_di"] is not None and t["minus_di"] > t["plus_di"] else "BULLISH_OR_NA"
                mom = "MOM3_DOWN" if t["momentum3"] is not None and t["momentum3"] < 0 else "MOM3_UP_OR_FLAT"
                groups[(dmi, mom)].append(t)
            for key, vals in sorted(groups.items()):
                print(f"    {key}: {concise(vals)}")
            for label, predicate in (
                ("ADX>=20", lambda t: t["adx"] is not None and t["adx"] >= 20),
                ("ADX>=20 + BULLISH_DMI", lambda t: t["adx"] is not None and t["adx"] >= 20 and t["minus_di"] is not None and t["plus_di"] is not None and t["plus_di"] >= t["minus_di"]),
                ("ADX>=20 + MOM3_UP", lambda t: t["adx"] is not None and t["adx"] >= 20 and t["momentum3"] is not None and t["momentum3"] >= 0),
            ):
                vals = [t for t in subset if predicate(t)]
                print(f"    FILTER {label}: {concise(vals)}")
    print("NOTE: exploratory search over multiple rules on a short, previously inspected October sample; no candidate is validated or production-approved.")
    print("Break-even decisive WR at 92% payout: 52.0833%.")


if __name__ == "__main__":
    main()
