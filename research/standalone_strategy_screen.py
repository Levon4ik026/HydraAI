#!/usr/bin/env python3
"""Standalone EURUSD M5 strategy-family screen. Research only; no execution.

Signals are computed from closed bars only. Entry is next M5 open; expiry is
the close of the Nth M5 bar after the signal. Gaps split the series.
"""
from __future__ import annotations
import argparse, csv, math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from long_history_validation import Bar, make_m5

PAYOUT = 0.92
HORIZONS = (1, 2, 3, 4, 6, 12)  # 5,10,15,20,30,60 minutes

def read_m1(path):
    rows = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        time_col = "datetime_utc" if "datetime_utc" in (rd.fieldnames or []) else "datetime" if "datetime" in (rd.fieldnames or []) else "timestamp"
        required = {time_col,"open","high","low","close"}
        if not required.issubset(rd.fieldnames or []):
            raise ValueError(f"Unexpected CSV header: {rd.fieldnames}")
        for r in rd:
            raw_time = r[time_col].strip()
            if time_col == "timestamp":
                ts = datetime.fromtimestamp(int(float(raw_time))/1000, tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                ts = ts.astimezone(timezone.utc)
            o,h,l,c = (float(r[k]) for k in ("open","high","low","close"))
            if all(math.isfinite(x) and x > 0 for x in (o,h,l,c)) and h >= max(o,l,c) and l <= min(o,c):
                rows[ts] = Bar(ts,o,h,l,c)
    return [rows[t] for t in sorted(rows)]

def rolling_mean(x, i, n):
    if i+1<n: return None
    return sum(x[i-n+1:i+1])/n

def rolling_std(x, i, n):
    m=rolling_mean(x,i,n)
    if m is None:return None
    return math.sqrt(sum((v-m)**2 for v in x[i-n+1:i+1])/n)

def build_specs():
    specs=[]
    # False break: pierce prior range, then close back inside; direction is reversal.
    for n in (12,24):
        specs += [(f"FALSE_BREAK_{n}_PUT", "fb_put", n, 0),
                  (f"FALSE_BREAK_{n}_CALL", "fb_call", n, 0)]
    # Momentum range breakout: close beyond previous range in breakout direction.
    for n in (12,24):
        specs += [(f"MOM_BREAK_{n}_CALL","mom_call",n,0),
                  (f"MOM_BREAK_{n}_PUT","mom_put",n,0)]
    # Mean reversion: normalized distance from rolling mean + reversal close.
    for n in (20,40):
        for z in (1.5,2.0):
            specs += [(f"MEAN_REV_{n}_Z{z}_CALL","mr_call",n,z),
                      (f"MEAN_REV_{n}_Z{z}_PUT","mr_put",n,z)]
    # Candle-only patterns: bullish/bearish engulfing and rejection pin bars.
    specs += [("ENGULF_CALL","engulf_call",0,0),("ENGULF_PUT","engulf_put",0,0),
              ("PIN_REJECT_CALL","pin_call",0,0),("PIN_REJECT_PUT","pin_put",0,0)]
    return specs

def signals_for_segment(bars, specs):
    c=[b.close for b in bars]; o=[b.open for b in bars]
    hi=[b.high for b in bars]; lo=[b.low for b in bars]
    out=defaultdict(list)
    for i in range(41, len(bars)-13):
        for name,kind,n,p in specs:
            side=None
            if kind.startswith("fb_"):
                ph=max(hi[i-n:i]); pl=min(lo[i-n:i])
                if kind=="fb_put" and hi[i]>ph and c[i]<ph and c[i]<o[i]: side="PUT"
                if kind=="fb_call" and lo[i]<pl and c[i]>pl and c[i]>o[i]: side="CALL"
            elif kind.startswith("mom_"):
                ph=max(hi[i-n:i]); pl=min(lo[i-n:i])
                if kind=="mom_call" and c[i]>ph and c[i]>o[i]: side="CALL"
                if kind=="mom_put" and c[i]<pl and c[i]<o[i]: side="PUT"
            elif kind.startswith("mr_"):
                m=rolling_mean(c,i-1,n); sd=rolling_std(c,i-1,n)
                if sd and sd>0:
                    z=(c[i-1]-m)/sd
                    if kind=="mr_call" and z<=-p and c[i]>o[i] and c[i]>c[i-1]: side="CALL"
                    if kind=="mr_put" and z>=p and c[i]<o[i] and c[i]<c[i-1]: side="PUT"
            elif kind.startswith("engulf_"):
                bull=(c[i-1]<o[i-1] and c[i]>o[i] and o[i]<=c[i-1] and c[i]>=o[i-1])
                bear=(c[i-1]>o[i-1] and c[i]<o[i] and o[i]>=c[i-1] and c[i]<=o[i-1])
                if kind=="engulf_call" and bull: side="CALL"
                if kind=="engulf_put" and bear: side="PUT"
            elif kind.startswith("pin_"):
                rng=hi[i]-lo[i]
                if rng>0:
                    lower=min(o[i],c[i])-lo[i]; upper=hi[i]-max(o[i],c[i])
                    if kind=="pin_call" and lower/rng>=0.60 and (c[i]-lo[i])/rng>=0.65: side="CALL"
                    if kind=="pin_put" and upper/rng>=0.60 and (hi[i]-c[i])/rng>=0.65: side="PUT"
            if side: out[name].append((i,side))
    return out

def outcome(bars,i,side,h):
    delta=bars[i+h].close-bars[i+1].open
    if abs(delta)<1e-12:return "D"
    return "W" if (delta>0)==(side=="CALL") else "L"

TRAIN_END_DATE = date(2025, 9, 17)
TEST_START_DATE = date(2026, 4, 14)


def split_dates(segments):
    # Frozen chronological boundaries: appending new history must not move
    # validation or TEST and must never reclassify already-scored candles.
    dates = sorted({b.timestamp.date() for segment in segments for b in segment})
    has_train = any(day < TRAIN_END_DATE for day in dates)
    has_validation = any(TRAIN_END_DATE <= day < TEST_START_DATE for day in dates)
    has_test = any(day >= TEST_START_DATE for day in dates)
    if not (has_train and has_validation and has_test):
        raise ValueError(
            "History must cover TRAIN before 2025-09-17, VALIDATION "
            "2025-09-17 through 2026-04-13, and TEST from 2026-04-14."
        )
    return TRAIN_END_DATE, TEST_START_DATE

def wilson_interval(wins, decisive, z=1.959963984540054):
    if decisive <= 0:
        return None
    p = wins / decisive
    den = 1.0 + z * z / decisive
    center = (p + z * z / (2.0 * decisive)) / den
    half = z * math.sqrt(
        p * (1.0 - p) / decisive + z * z / (4.0 * decisive * decisive)
    ) / den
    return 100.0 * (center - half), 100.0 * (center + half)


def summarize(outcomes):
    wins = sum(x == "W" for x in outcomes)
    losses = sum(x == "L" for x in outcomes)
    draws = sum(x == "D" for x in outcomes)
    total = len(outcomes)
    decisive = wins + losses
    wr = 100.0 * wins / decisive if decisive else None
    win_all = 100.0 * wins / total if total else None
    net = wins * PAYOUT - losses
    roi = 100.0 * net / total if total else None
    pf = wins * PAYOUT / losses if losses else (float("inf") if wins else 0.0)

    equity = peak = max_dd = 0.0
    current_streak = max_streak = 0
    for outcome in outcomes:
        if outcome == "W":
            equity += PAYOUT
            current_streak = 0
        elif outcome == "L":
            equity -= 1.0
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    return {
        "n": total, "w": wins, "l": losses, "d": draws,
        "wr": wr, "wilson": wilson_interval(wins, decisive),
        "win_all": win_all, "net": net, "roi": roi, "pf": pf,
        "max_dd": max_dd, "max_losing_streak": max_streak,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/STANDALONE_STRATEGY_SCREEN.md"))
    a=ap.parse_args()
    m1=read_m1(a.data); segments=make_m5(m1); d1,d2=split_dates(segments)
    specs=build_specs(); records=[]
    for sid,bars in enumerate(segments):
        sigs=signals_for_segment(bars,specs)
        for name,events in sigs.items():
            for h in HORIZONS:
                for i,side in events:
                    if i+h>=len(bars): continue
                    st=bars[i].timestamp.date(); et=bars[i+h].timestamp.date()
                    if st<d1:
                        period="TRAIN" if et<d1 else None
                    elif st<d2:
                        period="VALIDATION" if et<d2 else None
                    else: period="TEST"
                    if period:
                        records.append((name,h,sid,i,side,period,outcome(bars,i,side,h)))
    grouped=defaultdict(list)
    for r in records: grouped[(r[0],r[1],r[5])].append(r)
    # one-position trades independently per family and expiry, no overlap within segment
    nonoverlap=defaultdict(list)
    raw_by=defaultdict(list)
    for r in records: raw_by[(r[0],r[1],r[5],r[2])].append(r)
    for (name,h,period,sid),segment_rows in raw_by.items():
        next_i = -1
        for r in sorted(segment_rows, key=lambda x: x[3]):
            if r[3] >= next_i:
                nonoverlap[(name,h,period)].append(r)
                next_i = r[3] + h

    period_dates = {"TRAIN": set(), "VALIDATION": set(), "TEST": set()}
    period_bars = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0}
    for segment in segments:
        for bar in segment:
            day = bar.timestamp.date()
            period = "TRAIN" if day < d1 else "VALIDATION" if day < d2 else "TEST"
            period_dates[period].add(day)
            period_bars[period] += 1
    rows=["# Standalone EURUSD strategy-family screen","",
      f"Source: Dukascopy EURUSD M1 BID; {len(m1):,} M1 rows; {sum(map(len,segments)):,} complete M5 bars; {len(segments):,} gap-separated segments.",
      f"Coverage: {m1[0].timestamp.isoformat()} to {m1[-1].timestamp.isoformat()}.",
      f"Chronological split by calendar dates: TRAIN < {d1}; VALIDATION {d1} through {d2-timedelta(days=1)}; TEST >= {d2}.",
      "Families: false range breaks, momentum range breaks, mean reversion, engulfing, rejection pin bars.",
      "Parameters fixed before evaluation; no optimization. Closed M5 signal, next M5 open entry; expiry at close of Nth subsequent M5 bar.",
      "Horizon set: 5/10/15/20/30/60 minutes. Payout: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%.",
      "Raw events and one-position non-overlap are reported separately. Non-overlap is enforced within each individual strategy/expiry.",
      "No transaction cost or Pocket Option quote simulation: Dukascopy BID is not the platform's exact price stream.",
      "Exploratory screen with many tested combinations; top rows are not confirmatory evidence. Do not promote from TEST ranking; select on validation and verify prospectively.","",
      "## Results — non-overlapping schedule","",
      "| Family | Expiry | Period | Trades | W/L/D | Decisive WR [95% Wilson] | Wins / all | Net u | ROI | PF | Max DD u | Max loss streak | Raw signals | Trade freq / M5 bars | WAIT |",
      "|---|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, h, period in sorted(nonoverlap):
        trade_rows = sorted(nonoverlap[(name, h, period)], key=lambda r: (r[2], r[3]))
        summary = summarize([r[6] for r in trade_rows])
        raw_count = len(grouped[(name, h, period)])
        bars_in_period = max(1, period_bars[period])
        trade_freq = 100.0 * summary["n"] / bars_in_period
        wait_share = 100.0 - trade_freq
        ci = summary["wilson"]
        wr_text = "n/a" if summary["wr"] is None else f'{summary["wr"]:.2f}%'
        ci_text = "n/a" if ci is None else f'[{ci[0]:.2f}, {ci[1]:.2f}]%'
        all_text = "n/a" if summary["win_all"] is None else f'{summary["win_all"]:.2f}%'
        roi_text = "n/a" if summary["roi"] is None else f'{summary["roi"]:.2f}%'
        pf_text = "inf" if summary["pf"] == float("inf") else f'{summary["pf"]:.2f}'
        rows.append(
            f'| {name} | {h*5}m | {period} | {summary["n"]} | '
            f'{summary["w"]}/{summary["l"]}/{summary["d"]} | {wr_text} {ci_text} | '
            f'{all_text} | {summary["net"]:+.2f} | {roi_text} | {pf_text} | '
            f'{summary["max_dd"]:.2f} | {summary["max_losing_streak"]} | '
            f'{raw_count} | {trade_freq:.3f}% | {wait_share:.3f}% |'
        )
    rows += ["","## Raw event counts by family and expiry","",
      "| Family | Expiry | TRAIN | VALIDATION | TEST |","|---|---:|---:|---:|---:|"]
    for name,h in sorted({(r[0],r[1]) for r in records}):
        vals=[len(grouped[(name,h,p)]) for p in ("TRAIN","VALIDATION","TEST")]
        rows.append(f"| {name} | {h*5}m | {vals[0]} | {vals[1]} | {vals[2]} |")
    rows += ["",
      "*Trade frequency is accepted non-overlapping trades divided by complete M5 bars in that split; WAIT is its complement. Raw signals are shown separately. WAIT is per strategy, not a portfolio-level share; families can signal simultaneously.",
      "## Interpretation","",
      "- The Wilson interval is descriptive and treats decisive outcomes as independent; clustered and overlapping market regimes make it optimistic.",
      "- Compare TRAIN, VALIDATION and TEST separately. No row is selected by TEST performance.",
      "- All variants reuse the same short historical sample and are subject to multiple-testing and prior-exploration bias.",
      "- Dukascopy BID candles are not Pocket Option executable quotes; no platform payout variation, spread or latency is modeled.",
      "- No model was deployed and no trade was executed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(rows),encoding="utf-8")
    print(f"Wrote {a.out}; raw events={len(records):,}; M5 bars={sum(map(len,segments)):,}; splits={d1}/{d2}")

if __name__=="__main__": main()
