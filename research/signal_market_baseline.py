#!/usr/bin/env python3
"""Compare frozen BB/Williams signals with the same-regime non-signal market baseline.

The baseline uses next-M5 direction for all eligible signal-close candles in the
same causal regime, excluding every triggered signal timestamp. No outcomes are
used to define regimes. This is descriptive matched-context research, not proof
of incremental predictive value: observations can be serially dependent.
"""
from __future__ import annotations
import argparse
from pathlib import Path
try:
    from .win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger, feature_rows
    from .market_regime_audit import classify_regimes
except ImportError:
    from win_loss_feature_audit import SPLIT_DATE, load_m1, make_m5, parse_time, build_ledger, feature_rows
    from market_regime_audit import classify_regimes

PAYOUT = 0.92

def wilson(wins: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None, None
    p = wins / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    half = z*((p*(1-p)/n + z*z/(4*n*n))**0.5)/den
    return center-half, center+half

def rate_text(wins: int, n: int) -> str:
    if not n:
        return "—"
    lo, hi = wilson(wins, n)
    return f"{wins/n:.1%} [{lo:.1%},{hi:.1%}]"

def build_market_rows(segments, split, signal_times):
    """Return non-signal background observations keyed by period and regime."""
    rows = []
    for bars in segments:
        features = feature_rows(bars)
        states = classify_regimes(bars, features)
        for i in range(len(bars)-1):
            cur, nxt = bars[i], bars[i+1]
            if (nxt.timestamp-cur.timestamp).total_seconds() != 300:
                continue
            state = states[i]
            if state["regime"] is None or state["trend_bias"] is None:
                continue
            ts = cur.timestamp.isoformat()
            if ts in signal_times:
                continue
            period = "TRAIN" if cur.timestamp < split else "HOLDOUT"
            change = nxt.close-nxt.open
            rows.append({
                "signal_time": ts, "period": period,
                "regime": state["regime"], "bias": state["trend_bias"],
                "up": change > 1e-12, "down": change < -1e-12,
                "draw": abs(change) <= 1e-12,
            })
    return rows

def outcome_counts(rows, direction):
    wins = sum(bool(r["up"] if direction == "CALL" else r["down"]) for r in rows)
    draws = sum(bool(r["draw"]) for r in rows)
    return wins, len(rows)-wins-draws, draws

def fmt_net(w, l):
    return f"{PAYOUT*w-l:+.2f}"

def make_report(ledger, background, split):
    lines = [
        "# Signal vs same-regime market baseline",
        "",
        f"Frozen BB(20,2)/Williams %R(14) re-entry + ADX>=15; split={split}; payout=92%; next M5 candle outcome.",
        "Background = every eligible non-signal candle with a next contiguous M5 candle, matched by period and causal regime; all trigger timestamps are excluded.",
        "Regimes: prior-120-bar ATR14/close tertile × fixed ADX bands; directional bias = EMA20−EMA50 sign.",
        "Wilson 95% intervals are descriptive and do not correct serial dependence or overlapping market regimes.",
        "The background is a contextual benchmark, not an independent randomized control. No filter is selected.",
        "",
    ]
    signal_times = {x["signal_time"] for x in ledger}
    for direction in ("CALL", "PUT"):
        for period in ("TRAIN", "HOLDOUT"):
            sig = [x for x in ledger if x["direction"] == direction and x["period"] == period]
            bg = [x for x in background if x["period"] == period]
            lines += [f"## {direction} / {period}", "",
                      "### Directional bias matched baseline",
                      "| Bias | Signal n W/L/D | Signal WR (95% Wilson) | Signal net u | Background n W/L/D | Background WR (95% Wilson) | Lift |",
                      "|---|---:|---:|---:|---:|---:|---:|"]
            for bias in ("DOWN_BIAS","UP_BIAS","FLAT_BIAS"):
                s = [x for x in sig if x["features"]["ema20_50_atr"] is not None and
                     ("UP_BIAS" if x["features"]["ema20_50_atr"] > 0 else "DOWN_BIAS" if x["features"]["ema20_50_atr"] < 0 else "FLAT_BIAS") == bias]
                b = [x for x in bg if x["bias"] == bias]
                sw, sl, sd = outcome_counts(s, direction)
                bw, bl, bd = outcome_counts(b, direction)
                if not s and not b:
                    continue
                sr = sw/(sw+sl) if sw+sl else None
                br = bw/(bw+bl) if bw+bl else None
                lift = "—" if sr is None or br is None else f"{(sr-br)*100:+.1f} pp"
                lines.append(f"| {bias} | {len(s)} {sw}/{sl}/{sd} | {rate_text(sw,sw+sl)} | {fmt_net(sw,sl)} | {len(b)} {bw}/{bl}/{bd} | {rate_text(bw,bw+bl)} | {lift} |")
            lines += ["", "### Volatility × trend strength matched baseline",
                      "| Regime | Signal n W/L/D | Signal WR (95% Wilson) | Signal net u | Background n W/L/D | Background WR (95% Wilson) | Lift |",
                      "|---|---:|---:|---:|---:|---:|---:|"]
            names = sorted({x["regime"] for x in bg} | {x["regime"] for x in []})
            # Attach each signal's regime by causal features using the same fixed bins.
            # Signal regime is reconstructed from the full ledger feature rows and prior-120 ATR rank
            # via the timestamp lookup prepared by main().
            signal_state = SIGNAL_STATES
            names = sorted({x["regime"] for x in bg} | {signal_state[x["signal_time"]]["regime"] for x in sig if signal_state[x["signal_time"]]["regime"] is not None})
            for name in names:
                s = [x for x in sig if signal_state[x["signal_time"]]["regime"] == name]
                b = [x for x in bg if x["regime"] == name]
                sw, sl, sd = outcome_counts(s, direction)
                bw, bl, bd = outcome_counts(b, direction)
                sr = sw/(sw+sl) if sw+sl else None
                br = bw/(bw+bl) if bw+bl else None
                lift = "—" if sr is None or br is None else f"{(sr-br)*100:+.1f} pp"
                lines.append(f"| {name} | {len(s)} {sw}/{sl}/{sd} | {rate_text(sw,sw+sl)} | {fmt_net(sw,sl)} | {len(b)} {bw}/{bl}/{bd} | {rate_text(bw,bw+bl)} | {lift} |")
            lines.append("")
    lines += [
        "## Reading this comparison",
        "",
        "- A positive lift means the frozen signal's directional success rate exceeded the non-signal market baseline in the same period and regime.",
        "- Negative or near-zero lift suggests the signal may add little beyond the prevailing market context.",
        "- Small signal cells and wide Wilson intervals are inconclusive; compare train and holdout without pooling.",
        "- This is not causal proof: market candles are serially dependent, regime cells are observational, and the holdout was previously inspected.",
        "- Do not deploy a regime filter from this report. The next confirmation must be prospective on fresh continuous non-OTC data with frozen rules.",
    ]
    return "\n".join(lines)+"\n"

SIGNAL_STATES = {}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=Path("eurusd_history_extended.csv"))
    ap.add_argument("--split-date",default=SPLIT_DATE)
    ap.add_argument("--adx-min",type=float,default=15.0)
    ap.add_argument("--out",type=Path,default=Path("research/SIGNAL_MARKET_BASELINE.md"))
    args=ap.parse_args()
    m1=load_m1(args.data)
    segments=make_m5(m1)
    split=parse_time(args.split_date)
    ledger=build_ledger(segments,split,args.adx_min)
    states={}
    for bars in segments:
        for bar,state in zip(bars,classify_regimes(bars,feature_rows(bars))):
            states[bar.timestamp.isoformat()]=state
    global SIGNAL_STATES
    SIGNAL_STATES=states
    background=build_market_rows(segments,split,{x["signal_time"] for x in ledger})
    report=make_report(ledger,background,split.isoformat())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(report,encoding="utf-8")
    print(report)
    print(f"Eligible signals={len(ledger)}; non-signal baseline observations={len(background)}")

if __name__=="__main__":
    main()
