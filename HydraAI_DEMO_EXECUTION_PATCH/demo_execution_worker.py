from __future__ import annotations
import asyncio, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
from hydra_demo.pocket_option_demo import PocketOptionDemoAdapter
from hydra_demo.engine import DemoExecutionGate

BASE = Path(sys.executable).resolve().parents[1] if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
STATE_PATH = BASE / "observer_data" / "demo_execution_state.json"
ALLOWED_CANDIDATES = {"CAND-001", "CAND-008", "CAND-010", "CAND-012", "CAND-014"}
STAKE = 1
DAILY_LOSS_LIMIT = 3.0

def emit(status: str, **fields) -> None:
    print("HYDRA_EXECUTION|" + json.dumps({"status": status, **fields}, ensure_ascii=False, separators=(",", ":")), flush=True)

def parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None: raise ValueError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)

def load_state() -> dict:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        return {"date_utc": datetime.now(timezone.utc).date().isoformat(), "daily_loss_units": 0.0, "signals": {}, "halted": False}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("signals"), dict):
        raise RuntimeError("execution state is corrupt; refusing to trade")
    # A process crash can leave a persisted SUBMITTING record before the
    # exception handler marks it UNRESOLVED. Never clear that evidence on a
    # new UTC day: broker history must be reconciled manually first.
    unresolved = [
        key for key, item in state["signals"].items()
        if isinstance(item, dict) and item.get("status") in {"SUBMITTING", "UNRESOLVED"}
    ]
    if unresolved:
        state["halted"] = True
        state["halt_reason"] = "persisted order outcome requires manual broker-history reconciliation"
    today = datetime.now(timezone.utc).date().isoformat()
    if state.get("date_utc") != today and not state.get("halted"):
        state = {"date_utc": today, "daily_loss_units": 0.0, "signals": {}, "halted": False}
    return state

def save_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)

def candidate_rule_rejection(candidate_id: str) -> str | None:
    # CAND-010 is a directional downside breakout: a completed M5 candle
    # crosses and closes below the previous completed UTC-day low -> PUT.
    # A reclaim above that level is a separate reversal setup, not this rule.
    return None


def verification_rejection(data: dict, now: datetime) -> str | None:
    if data.get("status") != "VERIFIED":
        return "DEMO order verification status is not VERIFIED"
    try:
        verified_at = parse_utc(data["verified_at_utc"])
    except Exception:
        return "missing or invalid verification timestamp"
    age = (now - verified_at).total_seconds()
    if age < -60 or age > 30 * 24 * 3600:
        return "DEMO order verification is older than 30 days or timestamp is in the future"
    if data.get("asset") != "EURUSD" or data.get("is_demo") is not True:
        return "verification was not for DEMO EURUSD"
    if data.get("closed") is not True or not data.get("deal_id"):
        return "verification does not prove a closed broker deal"
    if data.get("amount") != 1 or data.get("expiry_seconds") != 300:
        return "verification must be a one-unit, five-minute DEMO order"
    return None


def adapter_verification_ok() -> bool:
    try:
        data = json.loads((BASE / "observer_data" / "demo_order_adapter_verified.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    return verification_rejection(data, datetime.now(timezone.utc)) is None


def market_rejection(snapshot: dict, expiry_minutes: int) -> str | None:
    if snapshot.get("status") != "ACTIVE": return f"market status {snapshot.get('status')}: {snapshot.get('reason', '')}"
    if snapshot.get("symbol") != "EURUSD" or snapshot.get("is_otc") is not False: return "asset identity mismatch or OTC is prohibited"
    if snapshot.get("active") is not True: return "EURUSD is inactive"
    payout = snapshot.get("payout_ratio")
    if not isinstance(payout, (int, float)) or not math.isfinite(payout) or payout < .92 or payout > 1: return "live payout is missing, invalid or below 92%"
    if expiry_minutes * 60 not in snapshot.get("timeframes_seconds", []): return f"expiry {expiry_minutes * 60}s is not offered by EURUSD"
    if float(snapshot.get("metadata_age_seconds", 999999)) > 45: return "broker asset metadata is stale"
    return None

def signal_rejection(command: dict, now: datetime) -> str | None:
    try:
        tick_time, entry_time = parse_utc(command["tick_time"]), parse_utc(command["entry_time"])
    except Exception as exc: return f"invalid signal timestamp: {exc}"
    tick_age, entry_age = (now-tick_time).total_seconds(), (now-entry_time).total_seconds()
    if tick_age < -2 or tick_age > 5: return f"live tick is stale ({tick_age:.1f}s)"
    if entry_age < -2 or entry_age > 8: return f"entry window expired ({entry_age:.1f}s)"
    return None

async def handle_signal(adapter: PocketOptionDemoAdapter, command: dict, state: dict) -> None:
    candidate_id, direction = str(command.get("candidate_id", "")), str(command.get("direction", "")).upper()
    expiry = int(command.get("expiry_minutes", 0))
    if candidate_id not in ALLOWED_CANDIDATES or direction not in {"CALL", "PUT"} or expiry not in {5, 30, 60}:
        emit("REJECTED", reason="invalid candidate/direction/expiry"); return
    rule_reason = candidate_rule_rejection(candidate_id)
    if rule_reason:
        emit("BLOCKED_SPEC", candidate_id=candidate_id, reason=rule_reason)
        return
    reason = signal_rejection(command, datetime.now(timezone.utc))
    if reason: emit("REJECTED", candidate_id=candidate_id, reason=reason); return
    snapshot = await adapter.get_market_snapshot()
    reason = market_rejection(snapshot, expiry)
    if reason: emit("REJECTED", candidate_id=candidate_id, reason=reason, market=snapshot); return
    if state.get("halted"): emit("HALTED", reason="manual review required"); return
    if float(state.get("daily_loss_units", 0.0)) + 1.0 > DAILY_LOSS_LIMIT:
        emit("DAILY_STOP", reason=f"next full-stake loss would exceed {DAILY_LOSS_LIMIT:.1f} units"); return
    signal_key = candidate_id + "|" + str(command.get("signal_time", ""))
    if signal_key in state["signals"]: emit("DUPLICATE_BLOCKED", candidate_id=candidate_id, signal_key=signal_key); return
    try:
        open_positions = await adapter.get_open_positions()
    except Exception as exc:
        emit("BLOCKED", candidate_id=candidate_id,
             reason=f"broker open-position state is unverified; no order sent: {exc}")
        return
    if not isinstance(open_positions, list):
        emit("BLOCKED", candidate_id=candidate_id,
             reason="broker open-position response is invalid; no order sent")
        return
    gate = DemoExecutionGate(account_mode="DEMO", instrument="EURUSD", otc=False,
                             broker_adapter_verified=adapter_verification_ok(), explicit_live_authorization=False)
    ok, gate_reason = gate.can_submit(feed_ok=True, payout=float(snapshot["payout_ratio"]),
                                     open_positions=len(open_positions),
                                     daily_loss_units=float(state.get("daily_loss_units", 0.0)),
                                     max_daily_loss_units=DAILY_LOSS_LIMIT)
    if not ok: emit("REJECTED", candidate_id=candidate_id, reason=gate_reason); return
    state["signals"][signal_key] = {"status":"SUBMITTING","candidate_id":candidate_id,
        "direction":direction,"entry_time":command["entry_time"],"created_at_utc":datetime.now(timezone.utc).isoformat()}
    save_state(state)
    emit("SUBMITTING", candidate_id=candidate_id, direction=direction, expiry_minutes=expiry,
         payout_percent=snapshot["payout_percent"], stake=STAKE)
    try:
        result = await adapter.open_and_wait(direction, expiry, payout=None)
        profit = float(result["profit"])
        if not math.isfinite(profit): raise RuntimeError("broker returned non-finite profit")
        net_units = float(snapshot["payout_ratio"]) if profit > 0 else (-1.0 if profit < 0 else 0.0)
        if net_units < 0: state["daily_loss_units"] = float(state.get("daily_loss_units", 0.0)) + abs(net_units)
        elif net_units > 0: state["daily_loss_units"] = max(0.0, float(state.get("daily_loss_units", 0.0)) - net_units)
        state["signals"][signal_key] = {"status":"CLOSED","candidate_id":candidate_id,"direction":direction,
            "deal_id":result["deal_id"],"profit":result["profit"],"net_units":net_units,
            "closed_at_utc":datetime.now(timezone.utc).isoformat()}
        save_state(state)
        emit("CLOSED", candidate_id=candidate_id, deal_id=result["deal_id"], direction=direction,
             profit=result["profit"], net_units=net_units, daily_loss_units=state["daily_loss_units"])
        if state["daily_loss_units"] >= DAILY_LOSS_LIMIT: emit("DAILY_STOP", reason="daily loss limit reached; new orders blocked")
    except Exception as exc:
        state["signals"][signal_key]["status"] = "UNRESOLVED"
        state["signals"][signal_key]["error"] = str(exc)
        state["halted"] = True
        save_state(state)
        emit("HALTED", candidate_id=candidate_id, reason="order outcome uncertain; no retry; manual broker-history check required", error=str(exc))

async def publish_market_status(adapter: PocketOptionDemoAdapter) -> None:
    while True:
        await asyncio.sleep(10)
        snapshot = await adapter.get_market_snapshot()
        emit("MARKET", market=snapshot)


async def main() -> int:
    if os.name != "nt": emit("ERROR", reason="Windows only"); return 2
    if os.getenv("HYDRA_DEMO_AUTOTRADE") != "1": emit("ERROR", reason="explicit GUI authorization required"); return 2
    if os.getenv("HYDRA_ACCOUNT_MODE", "DEMO").upper() != "DEMO": emit("ERROR", reason="REAL mode rejected"); return 2
    if os.getenv("HYDRA_INSTRUMENT", "EURUSD").upper() != "EURUSD" or os.getenv("HYDRA_ALLOW_OTC", "0") != "0":
        emit("ERROR", reason="only non-OTC EURUSD is permitted"); return 2
    if not adapter_verification_ok():
        emit("BLOCKED", reason="broker order adapter is not verified; run verify_demo_order.py and confirm one closed 1-unit DEMO EURUSD trade first")
        return 5
    state = load_state()
    if state.get("halted"): emit("HALTED", reason="previous unresolved order requires manual review"); return 3
    adapter = PocketOptionDemoAdapter(amount=STAKE)
    market_task = None
    try:
        await adapter.connect()
        market_task = asyncio.create_task(publish_market_status(adapter))
        snapshot = await adapter.get_market_snapshot()
        emit("READY", mode="DEMO", symbol="EURUSD", stake=STAKE, market=snapshot,
             daily_loss_units=state.get("daily_loss_units", 0.0))
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line: break
            try: command = json.loads(line)
            except json.JSONDecodeError: emit("REJECTED", reason="invalid JSON command"); continue
            if command.get("command") == "STOP":
                emit("STOPPING", reason="no new signals accepted; waiting for current operation"); break
            if state.get("halted"): emit("HALTED", reason="manual review required"); break
            await handle_signal(adapter, command, state)
            if state.get("halted"):
                emit("PAUSED", reason="risk halt active; no further trades")
                break
            if float(state.get("daily_loss_units", 0.0)) + 1.0 > DAILY_LOSS_LIMIT:
                emit("PAUSED", reason="next full-stake loss would exceed daily stop")
    except Exception as exc:
        emit("ERROR", reason=f"{type(exc).__name__}: {exc}"); return 4
    finally:
        if market_task is not None:
            market_task.cancel()
            try: await market_task
            except asyncio.CancelledError: pass
        try: await adapter.disconnect()
        except Exception: pass
    emit("STOPPED")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
