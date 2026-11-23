"""Five-candidate EURUSD shadow engine. No broker order submission."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta, date, time
from pathlib import Path
from typing import Optional, Iterable
from zoneinfo import ZoneInfo
import csv, math

NY = ZoneInfo("America/New_York")

@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float

@dataclass(frozen=True)
class FeedCheck:
    ok: bool
    reason: str
    count: int
    latest_age_seconds: Optional[float]

@dataclass(frozen=True)
class Signal:
    candidate_id: str
    candidate_name: str
    direction: str
    signal_time: str
    entry_time: str
    expiry_minutes: int
    entry_reference: float
    reason: str
    regime: str = "UNKNOWN"

@dataclass(frozen=True)
class Outcome:
    candidate_id: str
    signal_time: str
    entry_time: str
    expiry_time: str
    direction: str
    entry_price: float
    exit_price: Optional[float]
    result: str
    payout: float
    net_units: float


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None: return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _parse_time(value: str) -> datetime:
    return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))

def load_candles(path: str | Path) -> list[Candle]:
    rows=[]
    with Path(path).open("r", newline="", encoding="utf-8-sig") as f:
        reader=csv.DictReader(f); required={"datetime_utc","open","high","low","close"}
        if not required.issubset(reader.fieldnames or []): raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for row in reader:
            try:
                c=Candle(_parse_time(row["datetime_utc"]), float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]))
            except (TypeError, ValueError, KeyError): continue
            vals=(c.open,c.high,c.low,c.close)
            if not all(math.isfinite(x) and x>0 for x in vals): continue
            if c.high < max(c.open,c.close,c.low) or c.low > min(c.open,c.close,c.high): continue
            rows.append(c)
    rows.sort(key=lambda x:x.timestamp)
    dedup={c.timestamp:c for c in rows}
    return [dedup[k] for k in sorted(dedup)]

def check_feed(candles: list[Candle], now: Optional[datetime]=None, min_bars:int=60, max_age_seconds:int=180)->FeedCheck:
    if len(candles)<min_bars: return FeedCheck(False,f"need at least {min_bars} valid candles",len(candles),None)
    now=_utc(now or datetime.now(timezone.utc)); age=(now-candles[-1].timestamp).total_seconds()
    if age < -60: return FeedCheck(False,"latest candle is more than 60s in the future",len(candles),age)
    if age>max_age_seconds: return FeedCheck(False,f"stale feed: {age:.0f}s old",len(candles),age)
    for a,b in zip(candles[-min_bars:],candles[-min_bars+1:]):
        gap=(b.timestamp-a.timestamp).total_seconds()
        if not 50<=gap<=70: return FeedCheck(False,f"minute gap detected: {gap:.0f}s",len(candles),age)
    return FeedCheck(True,"fresh continuous feed",len(candles),age)

def ema(values:list[float], period:int)->list[Optional[float]]:
    out=[None]*len(values)
    if len(values)<period:return out
    alpha=2/(period+1); cur=sum(values[:period])/period; out[period-1]=cur
    for i in range(period,len(values)):
        cur=alpha*values[i]+(1-alpha)*cur; out[i]=cur
    return out

def rsi(values:list[float],period:int=14)->list[Optional[float]]:
    out=[None]*len(values)
    if len(values)<=period:return out
    gains=[max(values[i]-values[i-1],0) for i in range(1,len(values))]
    losses=[max(values[i-1]-values[i],0) for i in range(1,len(values))]
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    def calc(g,l): return 100.0 if l==0 and g>0 else 50.0 if l==0 else 100-100/(1+g/l)
    out[period]=calc(ag,al)
    for i in range(period+1,len(values)):
        ag=((period-1)*ag+gains[i-1])/period; al=((period-1)*al+losses[i-1])/period
        out[i]=calc(ag,al)
    return out

def aggregate_m5(candles:list[Candle])->list[Candle]:
    buckets={}
    for c in candles:
        t=c.timestamp.replace(second=0,microsecond=0); start=t.replace(minute=t.minute-t.minute%5)
        buckets.setdefault(start,[]).append(c)
    out=[]
    for start,group in sorted(buckets.items()):
        group.sort(key=lambda x:x.timestamp)
        if len(group)!=5 or any((b.timestamp-a.timestamp).total_seconds()!=60 for a,b in zip(group,group[1:])): continue
        if group[0].timestamp!=start: continue
        out.append(Candle(start,group[0].open,max(x.high for x in group),min(x.low for x in group),group[-1].close))
    return out

def _atr_series(m5:list[Candle], period:int=14)->list[Optional[float]]:
    out=[None]*len(m5); trs=[]
    for i,c in enumerate(m5):
        if i==0: trs.append(c.high-c.low)
        else:
            pc=m5[i-1].close; trs.append(max(c.high-c.low,abs(c.high-pc),abs(c.low-pc)))
        if i>=period-1: out[i]=sum(trs[i-period+1:i+1])/period
    return out

def candidate_signals(candles:list[Candle])->list[Signal]:
    """Evaluate all five candidates on completed candles only; no future candle is used for a trigger."""
    if len(candles)<60:return []
    m1_by_time={c.timestamp:c for c in candles}
    m5=aggregate_m5(candles); out=[]
    if len(m5)<55:return []
    # Reset all rolling indicators after any missing M5 interval; never bridge a data gap.
    e20=[None]*len(m5); e50=[None]*len(m5); r14=[None]*len(m5); atr=[None]*len(m5); segment_starts=[0]*len(m5)
    segment_start=0
    boundaries=[]
    for k in range(1,len(m5)):
        if (m5[k].timestamp-m5[k-1].timestamp).total_seconds()!=300:
            boundaries.append((segment_start,k)); segment_start=k
    boundaries.append((segment_start,len(m5)))
    for left,right in boundaries:
        for k in range(left,right): segment_starts[k]=left
        segment=m5[left:right]
        if len(segment)<14: continue
        vals=[x.close for x in segment]
        se20=ema(vals,20); se50=ema(vals,50); srsi=rsi(vals,14); satr=_atr_series(segment,14)
        e20[left:right]=se20; e50[left:right]=se50; r14[left:right]=srsi; atr[left:right]=satr
    # Previous completed UTC day/week levels, computed from M5 bars strictly before each signal bar.
    daily={}; weekly={}
    for c in m5:
        d=c.timestamp.date(); iso=c.timestamp.isocalendar(); wk=(iso.year,iso.week)
        daily.setdefault(d,[]).append(c); weekly.setdefault(wk,[]).append(c)
    day_low={d:min(x.low for x in arr) for d,arr in daily.items()}
    week_low={w:min(x.low for x in arr) for w,arr in weekly.items()}
    # CAND-001, 008, 010, 012 enter at the first M1 open of the next M5 bucket.
    # The first M1 candle may be the live, still-forming candle supplied by the observer.
    for i in range(1,len(m5)):
        c=m5[i]; entry_time=c.timestamp+timedelta(minutes=5); entry_candle=m1_by_time.get(entry_time)
        if entry_candle is None: continue
        if e20[i] is None or e50[i] is None: continue
        if r14[i] is not None and atr[i] is not None and r14[i]>=70 and c.close<c.open and e20[i]>e50[i]:
            # Percentile against the preceding 120 completed M5 ATR values (current excluded).
            prior=[x for x in atr[max(segment_starts[i],i-120):i] if x is not None]
            rank=(sum(x<=atr[i] for x in prior)/len(prior)*100) if len(prior)==120 else 0
            if len(prior)==120 and rank>67:
                out.append(Signal("CAND-001","RSI14 overbought + bearish M5","PUT",c.timestamp.isoformat(),entry_time.isoformat(),5,entry_candle.open,f"RSI14={r14[i]:.2f}; bearish M5; EMA20>EMA50; ATR percentile={rank:.1f}"))
        # CAND-008: previous completed UTC week low sweep and reclaim, bullish close.
        iso=c.timestamp.isocalendar(); current_week=(iso.year,iso.week)
        previous_weeks=[w for w in week_low if w<current_week]
        prev_key=max(previous_weeks) if previous_weeks else None
        if prev_key is not None and c.low<week_low[prev_key] and c.close>week_low[prev_key] and c.close>c.open:
            out.append(Signal("CAND-008","Previous UTC-week low sweep/reclaim","CALL",c.timestamp.isoformat(),entry_time.isoformat(),30,entry_candle.open,f"M5 swept and reclaimed prior UTC-week low {week_low[prev_key]:.5f}"))
        # CAND-010: close crosses below previous completed UTC-day low.
        previous_days=[d for d in day_low if d<c.timestamp.date()]
        prev_day=max(previous_days) if previous_days else None
        if prev_day is not None and i>0 and (c.timestamp-m5[i-1].timestamp).total_seconds()==300 and m5[i-1].close>=day_low[prev_day] and c.close<day_low[prev_day]:
            out.append(Signal("CAND-010","Previous UTC-day low breakdown","PUT",c.timestamp.isoformat(),entry_time.isoformat(),60,entry_candle.open,f"M5 close crossed below prior UTC-day low {day_low[prev_day]:.5f}"))
        # CAND-012: fresh bearish EMA20/EMA50 cross on completed M5.
        if i>0 and (c.timestamp-m5[i-1].timestamp).total_seconds()==300 and e20[i-1] is not None and e50[i-1] is not None and e20[i-1]>=e50[i-1] and e20[i]<e50[i] and c.close<e20[i]:
            out.append(Signal("CAND-012","EMA20/EMA50 bearish cross","CALL",c.timestamp.isoformat(),entry_time.isoformat(),5,entry_candle.open,"EMA20 crossed below EMA50; close below EMA20; approved inverse CALL"))
    # CAND-014: completed NY 18:00->17:00 session downside shock; enter next 18:00 M1.
    # Session candle timestamps are 18:00 through 16:59 NY (1380 minutes); 17:00-17:59 is excluded.
    sessions={}
    for c in candles:
        local=c.timestamp.astimezone(NY); tm=local.timetz().replace(tzinfo=None)
        if tm>=time(18,0): sid=local.date()+timedelta(days=1)
        elif tm<time(17,0): sid=local.date()
        else: continue
        sessions.setdefault(sid,[]).append(c)
    valid=[]
    for sid,arr in sorted(sessions.items()):
        arr.sort(key=lambda x:x.timestamp)
        start_local=datetime.combine(sid-timedelta(days=1),time(18,0),NY)
        expected_start=start_local.astimezone(timezone.utc)
        if not arr or arr[0].timestamp!=expected_start: continue
        # Expected timestamps: 23 trading hours; >=99% coverage; no gap >5 minutes.
        expected=1380; times=[x.timestamp for x in arr]
        if len(arr)<math.ceil(expected*.99): continue
        if any((b-a).total_seconds()>300 for a,b in zip(times,times[1:])): continue
        last_local=arr[-1].timestamp.astimezone(NY)
        if last_local.date()!=sid or last_local.time().replace(tzinfo=None)<time(16,59): continue
        ret=math.log(arr[-1].close/arr[0].open)
        valid.append((sid,arr,ret,expected_start))
    for j in range(20,len(valid)):
        sid,arr,ret,start_utc=valid[j]
        prior_abs=[abs(x[2]) for x in valid[j-20:j]]
        threshold=sum(prior_abs)/20
        if threshold>0 and ret<=-threshold:
            entry_local=datetime.combine(sid,time(18,0),NY); entry_utc=entry_local.astimezone(timezone.utc)
            entry=next((x for x in candles if x.timestamp==entry_utc),None)
            if entry is not None:
                out.append(Signal("CAND-014","NY downside shock rebound","CALL",arr[-1].timestamp.isoformat(),entry.timestamp.isoformat(),30,entry.open,f"NY session log return={ret:.5f}; prior-20 mean abs return={threshold:.5f}"))
    # Deterministic de-duplication.
    unique={(s.candidate_id,s.signal_time):s for s in out}
    return sorted(unique.values(),key=lambda s:(s.entry_time,s.candidate_id))

def resolve_outcomes(candles:list[Candle], signals:Iterable[Signal], payout:float=.92)->list[Outcome]:
    """Resolve signals only when the exact expiry minute is present; ties are draws."""
    by_time={c.timestamp:c for c in candles}; out=[]
    for s in signals:
        entry=_parse_time(s.entry_time); expiry=entry+timedelta(minutes=s.expiry_minutes-1)
        c=by_time.get(expiry)
        if c is None:
            if candles and max(x.timestamp for x in candles)>expiry:
                out.append(Outcome(s.candidate_id,s.signal_time,s.entry_time,expiry.isoformat(),s.direction.upper(),s.entry_reference,None,"VOID_MISSING_EXPIRY",payout,0.0))
            continue
        direction=s.direction.upper(); win=c.close>s.entry_reference if direction=="CALL" else c.close<s.entry_reference
        tie=c.close==s.entry_reference; result="DRAW" if tie else "WIN" if win else "LOSS"
        net=0.0 if tie else payout if win else -1.0
        out.append(Outcome(s.candidate_id,s.signal_time,s.entry_time,expiry.isoformat(),direction,s.entry_reference,c.close,result,payout,net))
    return out

def append_signal_log(path:str|Path, signals:Iterable[Signal])->int:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); rows=list(signals)
    if not rows:return 0
    exists=path.exists()
    with path.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(asdict(rows[0]).keys()))
        if not exists:w.writeheader()
        for x in rows:w.writerow(asdict(x))
    return len(rows)

def append_outcome_log(path:str|Path, outcomes:Iterable[Outcome])->int:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); rows=list(outcomes)
    if not rows:return 0
    exists=path.exists()
    with path.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(asdict(rows[0]).keys()))
        if not exists:w.writeheader()
        for x in rows:w.writerow(asdict(x))
    return len(rows)

class DemoExecutionGate:
    """Broker execution is locked; this release is observation/paper-evaluation only."""
    def __init__(self,*,account_mode="DEMO",instrument="EURUSD",otc=False,broker_adapter_verified=False,explicit_live_authorization=False):
        self.account_mode=account_mode.upper(); self.instrument=instrument.upper(); self.otc=otc; self.broker_adapter_verified=broker_adapter_verified; self.explicit_live_authorization=explicit_live_authorization
    def can_submit(self,*,feed_ok:bool,payout:float,open_positions:int,daily_loss_units:float,max_daily_loss_units:float=3.0)->tuple[bool,str]:
        if self.account_mode!="DEMO":return False,"account mode must be DEMO"
        if self.instrument!="EURUSD" or self.otc:return False,"only non-OTC EURUSD is permitted"
        if not self.broker_adapter_verified:return False,"broker order adapter is not verified; execution locked"
        if not feed_ok:return False,"feed is stale or discontinuous"
        if payout<.92:return False,"payout below configured 92% floor"
        if open_positions>=1:return False,"one-position limit reached"
        if daily_loss_units>=max_daily_loss_units:return False,"daily loss limit reached"
        return True,"risk checks passed"
    def can_submit_real(self)->bool:return self.account_mode=="REAL" and self.explicit_live_authorization and self.broker_adapter_verified