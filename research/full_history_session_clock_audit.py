#!/usr/bin/env python3
"""Full-history EURUSD intraday clock-time audit; no trades/signals are simulated."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("research/FULL_HISTORY_SESSION_CLOCK_AUDIT_2026-11-09.md"))
    a=ap.parse_args()
    d=pd.read_csv(a.data,parse_dates=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)
    ts=d.datetime_utc
    delta=ts.diff().dt.total_seconds()/60
    weekend=ts.dt.dayofweek>=5
    valid=(d.low<=d.open)&(d.low<=d.close)&(d.high>=d.open)&(d.high>=d.close)&(d.high>=d.low)
    jump=(d.open-d.close.shift()).abs()*10000
    cr=(d.high-d.low)*10000
    L=[
      "# HYDRA — full-history EUR/USD intraday clock-time audit","",
      f"Rows: {len(d):,}; coverage: {ts.min()} — {ts.max()}.",
      "Source: eurusd_research_clean.csv; SHA-256 recorded in prior audit: 5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c.","",
      "## Data integrity","",
      f"- Duplicate timestamps: {ts.duplicated().sum():,}; non-increasing steps: {(delta<=0).sum():,}.",
      f"- Gaps >1 minute: {(delta>1).sum():,}; absent minute slots inside those gaps: {int((delta[delta>1]-1).sum()):,}.",
      f"- Weekend rows: {weekend.sum():,}; invalid OHLC rows: {(~valid).sum():,}.",
      f"- Absolute open-to-previous-close jump >2 pips: {(jump>2).sum():,}; >5 pips: {(jump>5).sum():,}; >10 pips: {(jump>10).sum():,}.",
      f"- M1 range median/p90/p99/p99.9: {cr.median():.2f}/{cr.quantile(.9):.2f}/{cr.quantile(.99):.2f}/{cr.quantile(.999):.2f} pips.","",
      "The large count of absent minutes includes closed-market periods and long capture gaps; it is not treated as isolated feed failures. Each 30-minute window is retained only with at least 25 valid one-minute transitions.","",
      "## Method","",
      "- Weekends excluded; UTC timestamps converted separately to Europe/London and America/New_York using DST-aware IANA zones.",
      "- Per local date and 30-minute bin: path is the sum of absolute close-to-close changes only across exact one-minute steps; range is max(high)-min(low); signed return is last close minus first open.",
      "- Stability split: before/after 2026-03-01. At least 25 valid transitions per window.",
      "- This is a clock-time activity diagnostic, not an event-day causal study or a binary-options strategy test.",""
    ]
    for zone,label in [("Europe/London","London local time"),("America/New_York","New York local time")]:
        loc=ts.dt.tz_convert(zone); z=d.loc[loc.dt.dayofweek<5].copy(); ll=loc.loc[loc.dt.dayofweek<5]
        z["day"]=ll.dt.date; z["minute"]=ll.dt.hour*60+ll.dt.minute; z["bin"]=(z.minute//30)*30
        gap=z.datetime_utc.diff().dt.total_seconds()/60; z["step"]=z.close.diff().abs()*10000; z.loc[gap!=1,"step"]=np.nan
        z=z[(z.bin>=360)&(z.bin<1080)]
        q=z.groupby(["day","bin"]).agg(n=("step","count"),path=("step","sum"),hi=("high","max"),lo=("low","min"),op=("open","first"),cl=("close","last")).reset_index()
        q=q[q.n>=25].copy(); q["range"]=(q.hi-q.lo)*10000; q["signed"]=(q.cl-q.op)*10000
        q["date"]=pd.to_datetime(q.day); q["period"]=np.where(q.date<pd.Timestamp("2026-03-01"),"EARLIER","LATER")
        s=q.groupby("bin").agg(days=("day","nunique"),path=("path","median"),rng=("range","median"),signed=("signed","median")).reset_index()
        s=s[s.days>=80]
        L += [f"## {label}","", "| Rank | Bin | Days | Median path | Median range | Median signed |","|---:|---:|---:|---:|---:|---:|"]
        for i,r in enumerate(s.sort_values("path",ascending=False).head(8).itertuples(),1):
            L.append(f"| {i} | {int(r.bin//60):02d}:{int(r.bin%60):02d} | {int(r.days)} | {r.path:.2f} | {r.rng:.2f} | {r.signed:+.2f} |")
        L += ["","| Lowest bin | Days | Median path | Median range |","|---:|---:|---:|---:|"]
        for r in s.sort_values("path").head(5).itertuples():
            L.append(f"| {int(r.bin//60):02d}:{int(r.bin%60):02d} | {int(r.days)} | {r.path:.2f} | {r.rng:.2f} |")
        L += ["","### Selected-bin split stability","", "| Bin | Period | Days | Path | Range | Signed |","|---:|---|---:|---:|---:|---:|"]
        bins=([7*60,8*60,9*60,9*60+30,10*60,12*60,13*60,14*60,15*60,16*60,17*60] if zone=="Europe/London" else [7*60,8*60,8*60+30,9*60,9*60+30,10*60,11*60,12*60,13*60,14*60,15*60,16*60])
        for b in bins:
            v=q[q.bin==b]
            for p in ["EARLIER","LATER"]:
                x=v[v.period==p]
                if len(x): L.append(f"| {b//60:02d}:{b%60:02d} | {p} | {len(x)} | {x.path.median():.2f} | {x.range.median():.2f} | {x.signed.median():+.2f} |")
        L.append("")
    L += ["## Fixed clock windows around commonly watched times","",
      "These are all eligible weekdays, not dates selected because a release actually occurred.","",
      "| Local anchor | Window | Days | Median path | Median range | Median signed | Positive-day share |","|---|---|---:|---:|---:|---:|---:|"]
    anchors=[("London 08:00 open","Europe/London",480),("London 16:00","Europe/London",960),("London 17:00 close","Europe/London",1020),("NY 08:30 data time","America/New_York",510),("NY 09:30 cash open","America/New_York",570),("NY 12:00 midday","America/New_York",720),("NY 14:00","America/New_York",840)]
    for name,zone,m in anchors:
        loc=ts.dt.tz_convert(zone); z=d.copy(); z["day"]=loc.dt.date; z["m"]=loc.dt.hour*60+loc.dt.minute; z["wd"]=loc.dt.dayofweek<5
        gap=z.datetime_utc.diff().dt.total_seconds()/60; z["step"]=z.close.diff().abs()*10000; z.loc[gap!=1,"step"]=np.nan
        for label,lo,hi in [("PRE",m-30,m),("POST",m,m+30)]:
            vals=[]
            for day,v in z[z.wd&(z.m>=lo)&(z.m<hi)].groupby("day"):
                if v.step.count()>=25: vals.append((v.step.sum(),(v.high.max()-v.low.min())*10000,(v.close.iloc[-1]-v.open.iloc[0])*10000))
            x=np.asarray(vals)
            if len(x): L.append(f"| {name} | {label} | {len(x)} | {np.median(x[:,0]):.2f} | {np.median(x[:,1]):.2f} | {np.median(x[:,2]):+.2f} | {(x[:,2]>0).mean()*100:.1f}% |")
    L += ["","## Interpretation","",
      "1. Highest recurring activity is around 17:00 London / 12:00 New York, rather than the London 08:00 open or the generic NY 08:30 release clock.",
      "2. The 30 minutes after the NY 09:30 cash open have a negative median signed return and more down than up days in this sample. This is a post-hoc clock-time observation, not a proven PUT edge.",
      "3. The generic NY 08:30 clock window does not show a broad weekday volatility burst; actual CPI/NFP/event dates must be isolated from ordinary weekdays.",
      "4. Activity at several high-volume clock times is lower in the later period, warning against assuming a stationary volatility profile.","",
      "## Decision","",
      "- Do not add a clock-time CALL/PUT filter from this audit.",
      "- Preserve two hypotheses for a predeclared follow-up: elevated activity around 17:00 London / 12:00 NY, and possible downside asymmetry after NY 09:30.",
      "- Next test should use same-weekday/month controls, day-block uncertainty, fixed 5m/20m binary settlements, actual payout, and prospective Pocket Option DEMO confirmation.",
      "- No Desktop code, strategy parameters, or auto-trading behavior changed.",""]
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text("\n".join(L),encoding="utf-8")
    print(f"Wrote {a.out}; rows={len(d)}; invalid_OHLC={(~valid).sum()}")

if __name__=="__main__": main()
