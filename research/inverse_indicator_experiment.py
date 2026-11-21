#!/usr/bin/env python3
"""Chronological direct-vs-inverse indicator experiment on clean EURUSD M1 candles."""
import argparse
import numpy as np
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default="eurusd_research_clean.csv")
    ap.add_argument("--payout", type=float, default=0.92)
    args=ap.parse_args()
    d=pd.read_csv(args.csv,parse_dates=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)
    d["segment"]=(d.datetime_utc.diff().dt.total_seconds().fillna(60)!=60).cumsum()
    chunks=[]
    for _,g in d.groupby("segment",sort=False):
        x=g.copy(); c=x.close
        x["ema9"]=c.ewm(span=9,adjust=False,min_periods=9).mean()
        x["ema21"]=c.ewm(span=21,adjust=False,min_periods=21).mean()
        delta=c.diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
        rs=gain/loss.replace(0,np.nan); x["rsi14"]=100-100/(1+rs)
        ma=c.rolling(20,min_periods=20).mean(); sd=c.rolling(20,min_periods=20).std(ddof=0)
        x["bb_z"]=(c-ma)/sd
        x["mom5"]=c-c.shift(5)
        chunks.append(x)
    d=pd.concat(chunks).sort_index()
    rules={
      "EMA9_21_trend":np.where(d.ema9>d.ema21,1,np.where(d.ema9<d.ema21,-1,0)),
      "MOM5_trend":np.where(d.mom5>0,1,np.where(d.mom5<0,-1,0)),
      "RSI_extreme_momentum":np.where(d.rsi14>=70,1,np.where(d.rsi14<=30,-1,0)),
      "RSI_extreme_fade":np.where(d.rsi14>=70,-1,np.where(d.rsi14<=30,1,0)),
      "BB20_2SD_fade":np.where(d.bb_z<=-2,1,np.where(d.bb_z>=2,-1,0)),
    }
    cut=int(len(d)*.70); seg=d.segment.to_numpy(); close=d.close.to_numpy()
    entry=d.open.shift(-1).to_numpy()
    rows=[]
    for name,s in rules.items():
      s=np.asarray(s,dtype=float)
      for h in (1,3,5):
        exitp=d.close.shift(-h).to_numpy()
        valid=(s!=0)&np.isfinite(entry)&np.isfinite(exitp)&(seg==d.segment.shift(-h).to_numpy())
        ix=np.flatnonzero(valid)
        direct=((s[ix]>0)&(exitp[ix]>entry[ix]))|((s[ix]<0)&(exitp[ix]<entry[ix]))
        inverse=((s[ix]<0)&(exitp[ix]>entry[ix]))|((s[ix]>0)&(exitp[ix]<entry[ix]))
        decisive=direct|inverse
        for label,mask in (("TRAIN",ix<cut),("TEST",ix>=cut)):
          w=int(direct[mask].sum()); l=int(inverse[mask].sum()); n=w+l
          wr=w/n if n else np.nan; iw=l/n if n else np.nan
          rows.append([name,h,label,n,int((~decisive[mask]).sum()),wr,wr*(1+args.payout)-1,iw,iw*(1+args.payout)-1])
    out=pd.DataFrame(rows,columns=["strategy","expiry_min","split","decisive_n","draws","direct_winrate","direct_ev_per_unit","inverse_winrate","inverse_ev_per_unit"])
    print("Rows:",len(d),"from",d.datetime_utc.min(),"to",d.datetime_utc.max())
    print("Chronological split:",d.datetime_utc.iloc[cut])
    print(out.to_string(index=False,float_format=lambda v:f"{v:.5f}"))
if __name__=="__main__": main()
