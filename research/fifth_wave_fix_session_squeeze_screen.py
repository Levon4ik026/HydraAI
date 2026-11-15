#!/usr/bin/env python3
"""Fifth-wave EURUSD fix/session/compression discovery. Research only."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from reproduce_m5_bb_williams_adx import Bar

PAYOUT = 0.92
FORWARD_START = datetime(2026, 11, 15, tzinfo=timezone.utc)
PAYOUT_GRID = (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.95, 1.00)
CANDIDATES = [
    {"id":"HYD-NEW-001","name":"Tokyo fix post-reversal","family":"FX fixing reversal","zone":"Asia/Tokyo","fix":"09:55","side_rule":"fade the EURUSD return over the 60 minutes ending at the fix","expiry_min":15},
    {"id":"HYD-NEW-002","name":"ECB fix post-reversal","family":"FX fixing reversal","zone":"Europe/Berlin","fix":"14:15","side_rule":"fade the EURUSD return over the 60 minutes ending at the fix","expiry_min":15},
    {"id":"HYD-NEW-003","name":"London fix post-reversal","family":"FX fixing reversal","zone":"Europe/London","fix":"16:00","side_rule":"fade the EURUSD return over the 60 minutes ending at the fix","expiry_min":15},
    {"id":"HYD-NEW-004","name":"London opening-hour drift","family":"Local-session seasonality","zone":"Europe/London","fix":"08:00","side_rule":"fixed CALL at the first M5 open at 08:00 London time","expiry_min":30},
    {"id":"HYD-NEW-005","name":"M5 volatility-squeeze breakout","family":"Volatility compression/expansion","zone":"UTC","fix":None,"side_rule":"breakout direction after a 12-bar range falls in the bottom 20% of the preceding 96 rolling 12-bar ranges","expiry_min":15},
]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def load_m1(path: Path):
    parsed={}; conflicted=set()
    raw_rows=invalid=duplicates=out_of_range=0
    start=datetime(2024,1,1,tzinfo=timezone.utc)
    end=datetime(2026,11,15,tzinfo=timezone.utc)
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        required={"timestamp","open","high","low","close"}
        if not required.issubset(rd.fieldnames or []):
            raise ValueError(f"Unexpected CSV header: {rd.fieldnames}")
        for row in rd:
            raw_rows+=1
            try:
                stamp=int(float(row["timestamp"]))
                ts=datetime.fromtimestamp(stamp/1000 if stamp>10**11 else stamp,tz=timezone.utc)
                o,h,l,c=(float(row[k]) for k in ("open","high","low","close"))
                if not all(math.isfinite(x) and x>0 for x in (o,h,l,c)) or h<max(o,l,c) or l>min(o,c):
                    invalid+=1; continue
                if not start<=ts<end:
                    out_of_range+=1; continue
                b=Bar(ts,o,h,l,c)
            except Exception:
                invalid+=1; continue
            if ts in parsed:
                duplicates+=1
                if parsed[ts] != b: conflicted.add(ts)
            else: parsed[ts]=b
    for ts in conflicted: parsed.pop(ts,None)
    return [parsed[t] for t in sorted(parsed)], {
        "raw_rows":raw_rows,"valid_unique_rows":len(parsed),"invalid_rows":invalid,
        "duplicate_rows":duplicates,"conflicting_duplicate_timestamps":len(conflicted),
        "out_of_range_rows":out_of_range
    }

def make_m5(m1):
    buckets=defaultdict(list)
    for b in m1:
        start=b.timestamp.replace(minute=(b.timestamp.minute//5)*5,second=0,microsecond=0)
        buckets[start].append(b)
    complete=[]; incomplete=0
    for start,group in sorted(buckets.items()):
        group=sorted(group,key=lambda x:x.timestamp)
        expected=[start+timedelta(minutes=k) for k in range(5)]
        if [x.timestamp for x in group] != expected:
            incomplete+=1; continue
        complete.append(Bar(start,group[0].open,max(x.high for x in group),min(x.low for x in group),group[-1].close))
    segments=[]
    for b in complete:
        if not segments or b.timestamp-segments[-1][-1].timestamp != timedelta(minutes=5):
            segments.append([b])
        else: segments[-1].append(b)
    return segments,incomplete

def gap_stats(m1):
    gaps=[]
    for a,b in zip(m1,m1[1:]):
        mins=int((b.timestamp-a.timestamp).total_seconds()/60)
        if mins>1: gaps.append(mins-1)
    return {"gap_intervals":len(gaps),"missing_minutes":sum(gaps),"largest_missing_interval_minutes":max(gaps,default=0)}

def outcome(bars,i,side,h):
    delta=bars[i+h].close-bars[i+1].open
    if abs(delta)<1e-12: return "D"
    return "W" if (delta>0)==(side=="CALL") else "L"

def wilson(w,n):
    if n<=0:return None
    z=1.959963984540054; p=w/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(100*(center-half),3),round(100*(center+half),3)]

def stats(rows,payout=PAYOUT):
    xs=[r["outcome"] if isinstance(r,dict) else r for r in rows]
    w=xs.count("W"); l=xs.count("L"); d=xs.count("D"); dec=w+l; n=len(xs)
    net=w*payout-l
    gross_win=w*payout; gross_loss=l
    pf=(gross_win/gross_loss) if gross_loss else (None if not gross_win else "inf")
    eq=peak=dd=0.0; streak=mx=0
    for x in xs:
        eq += payout if x=="W" else -1 if x=="L" else 0
        peak=max(peak,eq); dd=max(dd,peak-eq)
        streak=streak+1 if x=="L" else 0; mx=max(mx,streak)
    active=len({r["signal_time"][:10] for r in rows if isinstance(r,dict)})
    return {"n":n,"w":w,"l":l,"d":d,"decisive":dec,
            "wr_pct":round(100*w/dec,3) if dec else None,
            "wilson_95_pct":wilson(w,dec),"net_units":round(net,4),
            "expectancy_units_per_trade":round(net/n,5) if n else None,
            "roi_pct":round(100*net/n,3) if n else None,
            "profit_factor":round(pf,4) if isinstance(pf,float) else pf,
            "max_drawdown_units":round(dd,4),"longest_losing_streak":mx,
            "active_days":active,"trades_per_active_day":round(n/max(1,active),3) if n else 0}

def block_bootstrap(rows, seed):
    by_day=defaultdict(list)
    for r in rows: by_day[r["signal_time"][:10]].append(r["outcome"])
    days=sorted(by_day)
    if len(days)<10:return None
    rng=random.Random(seed); vals=[]
    for _ in range(1200):
        sample=[]
        while len(sample)<len(days):
            start=rng.randrange(len(days))
            for k in range(5): sample.extend(by_day[days[(start+k)%len(days)]])
        w=sample.count("W"); l=sample.count("L")
        if w+l: vals.append(100*w/(w+l))
    if not vals:return None
    vals.sort()
    return [round(vals[int(.025*(len(vals)-1))],2),round(vals[int(.975*(len(vals)-1))],2)]

def add_event(store,cid,sid,i,side,h,extra=None):
    store[cid].append({"segment":sid,"index":i,"side":side,"h":h,**(extra or {})})

def build_events(segments):
    raw=defaultdict(list)
    fix_specs=[
        ("HYD-NEW-001","Asia/Tokyo",9,55),
        ("HYD-NEW-002","Europe/Berlin",14,15),
        ("HYD-NEW-003","Europe/London",16,0),
    ]
    for sid,bars in enumerate(segments):
        for i in range(11,len(bars)-1):
            entry_utc=bars[i].timestamp+timedelta(minutes=5)
            for cid,zone_name,hh,mm in fix_specs:
                local=entry_utc.astimezone(ZoneInfo(zone_name))
                if local.weekday()>=5 or (local.hour,local.minute)!=(hh,mm): continue
                if any(bars[j+1].timestamp-bars[j].timestamp!=timedelta(minutes=5) for j in range(i-11,i)):
                    continue
                pre_move=bars[i].close-bars[i-11].open
                if abs(pre_move)<1e-12: continue
                side="PUT" if pre_move>0 else "CALL"
                add_event(raw,cid,sid,i,side,3,{"pre_fix_return_pips":round(pre_move*10000,3),"local_event_date":local.date().isoformat()})
            local_entry=entry_utc.astimezone(ZoneInfo("Europe/London"))
            if local_entry.weekday()<5 and (local_entry.hour,local_entry.minute)==(8,0):
                add_event(raw,"HYD-NEW-004",sid,i,"CALL",6,{"local_event_date":local_entry.date().isoformat()})
        for i in range(119,len(bars)-3):
            prior=bars[i-12:i]
            comp_hi=max(b.high for b in prior); comp_lo=min(b.low for b in prior)
            current_range=comp_hi-comp_lo
            hist=[]
            for j in range(i-108,i-12):
                win=bars[j-11:j+1]
                hist.append(max(b.high for b in win)-min(b.low for b in win))
            if len(hist)!=96: continue
            threshold=sorted(hist)[int(.20*(len(hist)-1))]
            if current_range>threshold: continue
            b=bars[i]
            if b.close>comp_hi and b.close>b.open:
                add_event(raw,"HYD-NEW-005",sid,i,"CALL",3,{"compression_range_pips":round(current_range*10000,3),"hist_p20_pips":round(threshold*10000,3)})
            elif b.close<comp_lo and b.close<b.open:
                add_event(raw,"HYD-NEW-005",sid,i,"PUT",3,{"compression_range_pips":round(current_range*10000,3),"hist_p20_pips":round(threshold*10000,3)})
    return raw

def make_trades(segments,raw,d1,d2):
    all_trades=[]; summary={}
    for cid,events in raw.items():
        accepted=[]; overlap=0; boundary=0; next_by_segment={}
        for e in sorted(events,key=lambda x:(x["segment"],x["index"])):
            sid=e["segment"]; i=e["index"]; h=e["h"]; bars=segments[sid]
            if i+h>=len(bars): continue
            next_allowed=next_by_segment.get(sid,-1)
            if i<next_allowed: overlap+=1; continue
            next_by_segment[sid]=i+h
            signal_time=bars[i].timestamp+timedelta(minutes=5)
            entry_time=bars[i+1].timestamp
            settle_time=bars[i+h].timestamp+timedelta(minutes=5)
            sd=signal_time.date()
            period="TRAIN" if sd<d1 else "VALIDATION" if sd<d2 else "TEST"
            if (period=="TRAIN" and settle_time.date()>=d1) or (period=="VALIDATION" and settle_time.date()>=d2):
                boundary+=1; continue
            side=e["side"]
            row={"candidate_id":cid,"signal_time":signal_time.isoformat(),"entry_time":entry_time.isoformat(),
                 "settlement_time":settle_time.isoformat(),"side":side,"outcome":outcome(bars,i,side,h),
                 "inverse_outcome":outcome(bars,i,"PUT" if side=="CALL" else "CALL",h),
                 "call_outcome":outcome(bars,i,"CALL",h),"put_outcome":outcome(bars,i,"PUT",h),
                 "period":period,"local_event_date":e.get("local_event_date",""),
                 "pre_fix_return_pips":e.get("pre_fix_return_pips",""),
                 "compression_range_pips":e.get("compression_range_pips",""),
                 "hist_p20_pips":e.get("hist_p20_pips","")}
            accepted.append(row); all_trades.append(row)
        summary[cid]={"raw_events":len(events),"accepted_trades":len(accepted),
                      "overlap_suppressed":overlap,"boundary_purged":boundary,"trades":accepted}
    return all_trades,summary

def monthly(rows):
    groups=defaultdict(list)
    for r in rows: groups[r["signal_time"][:7]].append(r)
    out=[]
    for month,rs in sorted(groups.items()):
        s=stats(rs)
        out.append({"month_utc":month,"n":s["n"],"w":s["w"],"l":s["l"],"d":s["d"],
                    "wr_pct":s["wr_pct"],"net_92_units":round(s["w"]*PAYOUT-s["l"],4)})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--trades",type=Path,required=True)
    ap.add_argument("--worklog",type=Path,required=True)
    ap.add_argument("--forward-start",default=FORWARD_START.isoformat())
    a=ap.parse_args()
    forward_start=datetime.fromisoformat(a.forward_start.replace("Z","+00:00")).astimezone(timezone.utc)
    m1,integrity=load_m1(a.data)
    if len(m1)<100000: raise SystemExit(f"Insufficient M1 history: {len(m1)}")
    segments,incomplete=make_m5(m1); total_m5=sum(map(len,segments))
    if total_m5<10000 or len(segments)<2: raise SystemExit("Insufficient complete M5 history or unexpected continuity layout")
    dates=sorted({b.timestamp.date() for seg in segments for b in seg})
    d1=dates[int(.60*len(dates))]; d2=dates[int(.80*len(dates))]
    raw=build_events(segments)
    trades,detail=make_trades(segments,raw,d1,d2)
    results={}; m5_by_period=defaultdict(int)
    for seg in segments:
        for b in seg:
            day=b.timestamp.date()
            p="TRAIN" if day<d1 else "VALIDATION" if day<d2 else "TEST"
            m5_by_period[p]+=1
    for c in CANDIDATES:
        cid=c["id"]; rows=detail.get(cid,{}).get("trades",[]); per={}
        for period in ("TRAIN","VALIDATION","TEST"):
            subset=[r for r in rows if r["period"]==period]
            s=stats(subset)
            s["signal_frequency_pct"]=round(100*s["n"]/max(1,m5_by_period[period]),4)
            s["wait_share_pct"]=round(100-s["signal_frequency_pct"],4)
            s["payout_sensitivity"]={str(p):round(s["w"]*p-s["l"],4) for p in PAYOUT_GRID}
            s["monthly"]=monthly(subset)
            per[period]=s
        forward=[r for r in rows if datetime.fromisoformat(r["signal_time"])>=forward_start]
        fstats=stats(forward)
        baselines={}
        validation=[r for r in rows if r["period"]=="VALIDATION"]
        for side in ("CALL","PUT"):
            baselines[side]=stats([{"outcome":r[f"{side.lower()}_outcome"],"signal_time":r["signal_time"]} for r in validation])
        val=per["VALIDATION"]
        if val["n"]<30 or val["active_days"]<10:
            status="INSUFFICIENT_VALIDATION_SAMPLE"
        elif val["wr_pct"] is not None and val["wr_pct"]>=57 and val["net_units"]>0 and isinstance(val["profit_factor"],float) and val["profit_factor"]>1:
            status="PRELIMINARILY_PROMISING_NOT_CONFIRMED"
        elif val["net_units"]>0 and val["wr_pct"] is not None and val["wr_pct"]>52.083:
            status="POSITIVE_BUT_BELOW_57_WR_SCREEN"
        else:
            status="SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET"
        results[cid]={"candidate":c,"status":status,"batch_eligible":val["n"]>=30 and val["active_days"]>=10,
                      "raw_events":detail.get(cid,{}).get("raw_events",0),
                      "accepted_trades":detail.get(cid,{}).get("accepted_trades",0),
                      "overlap_suppressed":detail.get(cid,{}).get("overlap_suppressed",0),
                      "boundary_purged":detail.get(cid,{}).get("boundary_purged",0),
                      "periods":per,"forward_since_2026_11_15":fstats,
                      "matched_same_timestamp_baselines_validation":baselines,
                      "validation_5day_block_bootstrap_wr_95_pct":block_bootstrap(validation,20261115+int(cid[-3:]))}
    batch_count=sum(1 for v in results.values() if v["batch_eligible"])
    raw_hash=sha256(a.data); config_hash=hashlib.sha256(json.dumps(CANDIDATES,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    manifest={
        "captured_at_utc":datetime.now(timezone.utc).isoformat(),"branch":"hydra/research-validation",
        "dataset":{"source":"Dukascopy EURUSD M1 BID","first_utc":m1[0].timestamp.isoformat(),"last_utc":m1[-1].timestamp.isoformat(),
                   "m1_integrity":integrity,"m1_gaps":gap_stats(m1),"complete_m5_bars":total_m5,
                   "incomplete_m5_buckets":incomplete,"continuity_segments":len(segments),"raw_csv_sha256":raw_hash},
        "split":{"train_before_utc_date":d1.isoformat(),"validation_before_utc_date":d2.isoformat(),
                 "train_ratio_target":0.60,"validation_ratio_target":0.20,"test_is_historically_exposed_not_pristine":True},
        "payout":{"scenario":0.92,"win_units":0.92,"loss_units":-1,"draw_units":0,"breakeven_decisive_wr_pct":52.0833,"sensitivity_grid":PAYOUT_GRID},
        "forward_start_utc":forward_start.isoformat(),"candidate_config_sha256":config_hash,"script_sha256":sha256(Path(__file__)),
        "batch_eligible_count":batch_count,"batch_size":5,"batch_ready":batch_count==5,
        "candidate_results":results,
        "execution_caveat":"Dukascopy BID is a research proxy, not Pocket Option executable pricing; spread, quote construction, actual payout, latency and settlement are not modeled.",
        "interpretation":"Historical validation is a screening set, not independent confirmation. TEST has prior broad research exposure. New prospective evidence begins only at the forward-start timestamp."
    }
    for path in (a.manifest,a.report,a.trades,a.worklog): path.parent.mkdir(parents=True,exist_ok=True)
    with a.trades.open("w",newline="",encoding="utf-8") as f:
        fields=["candidate_id","signal_time","entry_time","settlement_time","side","outcome","inverse_outcome","call_outcome","put_outcome","period","local_event_date","pre_fix_return_pips","compression_range_pips","hist_p20_pips"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(trades)
    a.manifest.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=[
      "# HydraAI — fifth-wave high-WR candidate screen","",
      f"- Captured UTC: {manifest['captured_at_utc']}",
      "- Branch: hydra/research-validation",
      f"- Source: Dukascopy EURUSD M1 BID; {integrity['valid_unique_rows']:,} valid unique M1 rows; {total_m5:,} complete M5 bars; {len(segments)} continuity segments.",
      f"- Coverage: {m1[0].timestamp.isoformat()} — {m1[-1].timestamp.isoformat()}",
      f"- M1 gaps: {manifest['dataset']['m1_gaps']['gap_intervals']} intervals; {manifest['dataset']['m1_gaps']['missing_minutes']} missing minutes; largest {manifest['dataset']['m1_gaps']['largest_missing_interval_minutes']} minutes.",
      f"- Invalid rows: {integrity['invalid_rows']}; duplicate rows: {integrity['duplicate_rows']}; conflicting duplicate timestamps: {integrity['conflicting_duplicate_timestamps']}; incomplete M5 buckets: {incomplete}.",
      f"- Raw CSV SHA-256: {raw_hash}; candidate config SHA-256: {config_hash}; script SHA-256: {manifest['script_sha256']}.",
      f"- Chronological split by observed UTC dates: TRAIN before {d1}; VALIDATION {d1}–{d2-timedelta(days=1)}; TEST from {d2}.",
      "- Important: historical TEST is not pristine; the repository has prior broad strategy exploration on overlapping history. Validation is a screening set, not independent proof.",
      "- Signals use completed M5 candles and next M5 open entry. Outcomes settle at the close of the M5 bar corresponding to the fixed expiry. Trades never bridge incomplete M5 buckets or continuity gaps.",
      "- Payout accounting: +0.92u WIN, -1u LOSS, 0u DRAW. Breakeven decisive WR = 52.0833%.",
      "- New prospective cohort starts 2026-11-15 00:00 UTC. Dukascopy data before that time is historical, even if some dates were not in older screens.",
      "","## Candidate summary","",
      "| ID | Candidate / market situation | Side | Expiry | VALIDATION N | W/L/D | WR | 95% Wilson | Net @92% | PF | Max DD | Max L streak | 5-day block WR CI | Status |",
      "|---|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---|---|"
    ]
    for c in CANDIDATES:
        r=results[c["id"]]; v=r["periods"]["VALIDATION"]; ci=v["wilson_95_pct"]; bci=r["validation_5day_block_bootstrap_wr_95_pct"]
        wr="n/a" if v["wr_pct"] is None else f"{v['wr_pct']:.2f}%"
        ci_txt="n/a" if ci is None else f"[{ci[0]:.2f}, {ci[1]:.2f}]%"
        bci_txt="n/a" if bci is None else f"[{bci[0]:.2f}, {bci[1]:.2f}]%"
        pf="n/a" if v["profit_factor"] is None else str(v["profit_factor"])
        lines.append(f"| {c['id']} | {c['name']} | {c['side_rule']} | {c['expiry_min']}m | {v['n']} | {v['w']}/{v['l']}/{v['d']} | {wr} | {ci_txt} | {v['net_units']:+.2f}u | {pf} | {v['max_drawdown_units']:.2f}u | {v['longest_losing_streak']} | {bci_txt} | {r['status']} |")
    lines += ["","## Exact candidate cards",""]
    for c in CANDIDATES:
        r=results[c["id"]]
        if c["id"] in ("HYD-NEW-001","HYD-NEW-002","HYD-NEW-003"):
            rule=f"At each weekday {c['fix']} local time in {c['zone']}, use the 12 complete M5 bars from fix−60m through fix−5m. If the 60m EURUSD move is positive, enter PUT; if negative, enter CALL. Signal is known at the fix; enter at the M5 open exactly at the fix."
            regime="Fix-window order-flow / benchmark rebalancing; fade the pre-fix EURUSD move."
        elif c["id"]=="HYD-NEW-004":
            rule="At the first eligible M5 open at 08:00 Europe/London on weekdays, enter CALL. The preceding 07:55–08:00 M5 bar is the completed timing bar; no price filter."
            regime="London local-session opening-hour seasonal drift."
        else:
            rule="On a completed M5 bar, require the immediately preceding 12-bar high-low range to be no greater than the 20th percentile of the 96 earlier rolling 12-bar ranges (all reference windows end before the current signal bar). Enter CALL on a bullish close above the prior 12-bar high; enter PUT on a bearish close below the prior 12-bar low. Entry next M5 open."
            regime="Low-volatility compression followed by directional range expansion."
        v=r["periods"]["VALIDATION"]; t=r["periods"]["TEST"]; f=r["forward_since_2026_11_15"]
        lines += [f"### {c['id']} — {c['name']}","",
          f"- Family / market state: {c['family']}; {regime}",
          f"- Exact entry rule: {rule}",
          f"- Direction / expiry: direction as above; {c['expiry_min']} minutes.",
          f"- Raw events / accepted trades: {r['raw_events']} / {r['accepted_trades']}; overlap suppressed {r['overlap_suppressed']}; split-boundary purged {r['boundary_purged']}.",
          f"- VALIDATION: N={v['n']}, W/L/D={v['w']}/{v['l']}/{v['d']}, decisive WR={v['wr_pct']}%, net={v['net_units']:+.2f}u, expectancy={v['expectancy_units_per_trade']}u/trade, PF={v['profit_factor']}, max DD={v['max_drawdown_units']}u, longest loss streak={v['longest_losing_streak']}, frequency={v['signal_frequency_pct']}% of M5 bars, WAIT={v['wait_share_pct']}%.",
          f"- TRAIN: N={r['periods']['TRAIN']['n']}, WR={r['periods']['TRAIN']['wr_pct']}%, net={r['periods']['TRAIN']['net_units']:+.2f}u. TEST (historically exposed): N={t['n']}, WR={t['wr_pct']}%, net={t['net_units']:+.2f}u.",
          f"- Same-timestamp baselines on VALIDATION: always CALL WR={r['matched_same_timestamp_baselines_validation']['CALL']['wr_pct']}%, net={r['matched_same_timestamp_baselines_validation']['CALL']['net_units']:+.2f}u; always PUT WR={r['matched_same_timestamp_baselines_validation']['PUT']['wr_pct']}%, net={r['matched_same_timestamp_baselines_validation']['PUT']['net_units']:+.2f}u; theoretical random-direction reference=50% decisive WR / −0.04u per trade at 92%.",
          f"- VALIDATION payout sensitivity: "+", ".join(f"{p:.0%}: {v['payout_sensitivity'][str(p)]:+.2f}u" for p in PAYOUT_GRID),
          f"- VALIDATION monthly stability: "+("; ".join(f"{m['month_utc']}: n={m['n']} WR={m['wr_pct']}% net={m['net_92_units']:+.2f}u" for m in v["monthly"]) or "no trades"),
          f"- New prospective cohort since 2026-11-15: N={f['n']}, W/L/D={f['w']}/{f['l']}/{f['d']}, WR={f['wr_pct']}%, net={f['net_units']:+.2f}u.",
          f"- Status: **{r['status']}**; batch-eligible (validation N≥30 and ≥10 active UTC days): {r['batch_eligible']}.",
          "- Limitations: Dukascopy BID is not Pocket Option executable pricing; no spread, latency, platform payout or settlement model. Fixing candidates share one literature mechanism and are correlated hypotheses, not three independent replications.",
          ""]
    lines += ["## Interpretation","",
      f"- Batch eligibility: {batch_count}/5 candidates meet the predeclared minimum of at least 30 VALIDATION trades and 10 active UTC days. Batch-ready={manifest['batch_ready']}.",
      "- A candidate is only preliminarily promising if VALIDATION WR≥57%, net @92% >0 and PF>1; this is a screening label, not confirmation.",
      "- Wilson intervals assume independent decisive outcomes; 5-day moving-block bootstrap is descriptive and does not remove all serial dependence or multiple-testing bias.",
      "- Historical TEST was previously exposed to broad repository research. The only new prospective cohort begins 2026-11-15; early forward N is expected to be small.",
      "- No rules were tuned on TEST. No production, stabilization, real trading, OTC or auto-trading code was changed.",
      "","## Literature used only to motivate hypotheses","",
      "- Krohn, Mueller & Whelan, “Foreign Exchange Fixings and Returns around the Clock”, Journal of Finance 79(1), first published 18 Dec 2023: https://doi.org/10.1111/jofi.13306",
      "- Breedon & Ranaldo, “Intraday Patterns in FX Returns and Order Flow”, Swiss National Bank Working Paper 2011-04, 23 Mar 2011: https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04",
      "- Ito & Hashimoto, “Intra-Day Seasonality in Activities of the Foreign Exchange Markets”, NBER Working Paper 12413, Aug 2006: https://www.nber.org/papers/w12413",
      "","## Reproducibility","",
      "- Machine-readable manifest: manifest.json; trade ledger: trades.csv (workflow artifact).",
      "- Source dataset SHA-256 and exact candidate configuration hash are recorded in the manifest.",""]
    a.report.write_text("\n".join(lines),encoding="utf-8")
    log=["# HydraAI high-WR discovery worklog","",
         f"- Latest screen: {manifest['captured_at_utc']}",
         "- Branch: hydra/research-validation",
         f"- Candidate batch eligibility: {batch_count}/5; batch_ready={manifest['batch_ready']}",
         "- Dedupe check: no exact match found in the existing prior-period sweep/reclaim, indicator, abnormal-impulse or three-candidate forward definitions. Three fix-window variants are related by one published mechanism and are not independent evidence.",""]
    for c in CANDIDATES:
        r=results[c["id"]]; v=r["periods"]["VALIDATION"]
        log += [f"## {c['id']} — {c['name']}","",
                f"- Fixed rules: {json.dumps(c,ensure_ascii=False)}",
                f"- Validation N={v['n']}; W/L/D={v['w']}/{v['l']}/{v['d']}; WR={v['wr_pct']}%; net@92={v['net_units']:+.2f}u; status={r['status']}.",
                f"- New prospective N since 2026-11-15: {r['forward_since_2026_11_15']['n']}.",""]
    a.worklog.write_text("\n".join(log),encoding="utf-8")
    print(json.dumps({"batch_eligible_count":batch_count,"batch_ready":manifest["batch_ready"],
                      "report":str(a.report),"manifest":str(a.manifest),"trades":str(a.trades)},ensure_ascii=False))

if __name__=="__main__": main()
