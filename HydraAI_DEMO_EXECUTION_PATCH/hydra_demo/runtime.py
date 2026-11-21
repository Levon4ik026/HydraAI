"""Forward-only candidate monitor with regime-tagged outcomes."""
from __future__ import annotations
from dataclasses import asdict, replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import csv
from collections import defaultdict
from bisect import bisect_right
from .engine import Signal, candidate_signals, append_signal_log, append_outcome_log, resolve_outcomes
from .adaptive import classify_regime, CandidateStats, select_candidate

CANDIDATES = ("CAND-001", "CAND-008", "CAND-010", "CAND-012", "CAND-014")

class CandidateMonitor:
    def __init__(self, data_dir: str | Path, started_at: datetime | None = None, payout: float = .92, min_trades: int = 100, max_drawdown_units: float = 3.0):
        self.data_dir=Path(data_dir); self.data_dir.mkdir(parents=True,exist_ok=True)
        self.signal_path=self.data_dir/"candidate_signals.csv"
        self.outcome_path=self.data_dir/"candidate_outcomes.csv"
        self.started_at=(started_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.payout=float(payout); self.min_trades=int(min_trades); self.max_drawdown_units=float(max_drawdown_units)
        self.seen_signals=set(); self.seen_outcomes=set()
        self._migrate_signal_log()
        self._restore_seen()

    def _migrate_signal_log(self):
        """Add the regime column without discarding earlier observation rows."""
        if not self.signal_path.exists(): return
        with self.signal_path.open("r",newline="",encoding="utf-8") as f:
            reader=csv.DictReader(f); fields=list(reader.fieldnames or []); rows=list(reader)
        if "regime" in fields: return
        fields.append("regime")
        tmp=self.signal_path.with_suffix(".csv.tmp")
        with tmp.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
            for row in rows: row["regime"]="UNKNOWN"; w.writerow(row)
        tmp.replace(self.signal_path)

    def _restore_seen(self):
        if self.signal_path.exists():
            with self.signal_path.open("r",newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f): self.seen_signals.add((row["candidate_id"],row["signal_time"]))
        if self.outcome_path.exists():
            with self.outcome_path.open("r",newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f): self.seen_outcomes.add((row["candidate_id"],row["signal_time"]))

    def process(self, candles, feed_ok: bool, completed_candles=None, allow_new_signals: bool = True, eligible_candidates: set[str] | None = None):
        if not feed_ok: return {"new_signals":0,"new_outcomes":0,"new_signal_records":[],"blocked":"feed is not fresh/continuous","regime":"UNKNOWN","selected_candidate":None,"selection_reason":"WAIT: feed blocked"}
        regime_candles = completed_candles if completed_candles is not None else candles
        regime=classify_regime(regime_candles)
        found=candidate_signals(candles) if allow_new_signals else []
        fresh=[]
        candle_times=[c.timestamp for c in regime_candles]
        for signal in found:
            key=(signal.candidate_id,signal.signal_time)
            if key in self.seen_signals: continue
            # Forward-only: ignore historical entries before this monitor session.
            if datetime.fromisoformat(signal.entry_time).astimezone(timezone.utc) < self.started_at: continue
            # Freeze the regime using only bars available at the signal timestamp.
            signal_dt=datetime.fromisoformat(signal.entry_time.replace("Z", "+00:00")).astimezone(timezone.utc)-timedelta(minutes=1)
            end=bisect_right(candle_times,signal_dt)
            signal_regime=classify_regime(regime_candles[max(0,end-60):end])
            fresh.append(replace(signal,regime=signal_regime.name))
        n_signals=append_signal_log(self.signal_path,fresh)
        for signal in fresh: self.seen_signals.add((signal.candidate_id,signal.signal_time))

        pending=[]
        if self.signal_path.exists():
            with self.signal_path.open("r",newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    key=(row["candidate_id"],row["signal_time"])
                    if key in self.seen_outcomes: continue
                    try:
                        pending.append(Signal(row["candidate_id"],row["candidate_name"],row["direction"],row["signal_time"],row["entry_time"],int(row["expiry_minutes"]),float(row["entry_reference"]),row["reason"],row.get("regime") or "UNKNOWN"))
                    except (KeyError,ValueError): continue
        resolved=resolve_outcomes(completed_candles if completed_candles is not None else candles,pending,self.payout)
        new_out=[o for o in resolved if (o.candidate_id,o.signal_time) not in self.seen_outcomes]
        n_outcomes=append_outcome_log(self.outcome_path,new_out)
        for outcome in new_out: self.seen_outcomes.add((outcome.candidate_id,outcome.signal_time))

        stats=self._forward_stats()
        if eligible_candidates is not None:
            stats=[item for item in stats if item.candidate_id in eligible_candidates]
        selected,why=select_candidate(regime,stats,payout=self.payout,min_trades=self.min_trades,max_drawdown_units=self.max_drawdown_units)
        return {"new_signals":n_signals,"new_outcomes":n_outcomes,"blocked":None,"signals_total":len(self.seen_signals),"outcomes_total":len(self.seen_outcomes),"regime":regime.name,"regime_confidence":regime.confidence,"regime_details":regime.details,"selected_candidate":selected,"selection_reason":why,"candidate_stats":stats,"new_signal_records":[asdict(s) for s in fresh]}

    def _forward_stats(self):
        if not self.signal_path.exists() or not self.outcome_path.exists(): return []
        with self.signal_path.open("r",newline="",encoding="utf-8") as f:
            regimes={(r["candidate_id"],r["signal_time"]):(r.get("regime") or "UNKNOWN") for r in csv.DictReader(f)}
        groups=defaultdict(list)
        with self.outcome_path.open("r",newline="",encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("result") not in {"WIN","LOSS","DRAW"}: continue
                key=(row["candidate_id"],row["signal_time"]); regime=regimes.get(key,"UNKNOWN")
                try: groups[(key[0],regime)].append((row["expiry_time"],row["result"],float(row["net_units"]),float(row["payout"])))
                except (KeyError,ValueError): continue
        stats=[]
        for (candidate_id,regime),items in groups.items():
            items.sort(key=lambda x:x[0]); wins=sum(x[1]=="WIN" for x in items); losses=sum(x[1]=="LOSS" for x in items); draws=sum(x[1]=="DRAW" for x in items)
            equity=peak=max_dd=0.0
            for _,result,net,_ in items:
                if result not in {"WIN","LOSS"}: continue
                equity+=net; peak=max(peak,equity); max_dd=max(max_dd,peak-equity)
            payout=min((x[3] for x in items if x[1] in {"WIN","LOSS"}),default=self.payout)
            stats.append(CandidateStats(candidate_id,regime,wins,losses,draws,max_dd,payout))
        return stats