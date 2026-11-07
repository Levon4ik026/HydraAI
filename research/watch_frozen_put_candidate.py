#!/usr/bin/env python3
"""Watch a continuously appended EURUSD M1 CSV and score the frozen PUT rule.

Research-only observer. It never places orders and never changes the frozen rule.
The forward boundary is created on first launch (next UTC M5 boundary) and
persisted in a state file so restarts cannot move it or backfill old candles.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from frozen_put_candidate import build_candidate, parse_utc  # noqa: E402
from reproduce_m5_bb_williams_adx import Bar, make_m5  # noqa: E402
from statistical_validation import wilson_interval  # noqa: E402


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def next_m5_boundary(now: datetime) -> datetime:
    floored = now.replace(second=0, microsecond=0)
    remainder = floored.minute % 5
    return floored + timedelta(minutes=(5 - remainder) % 5 or 5)


def load_m1(path: Path) -> list[Bar]:
    parsed: dict[datetime, Bar] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        time_col = "datetime_utc" if "datetime_utc" in fields else "datetime"
        required = {time_col, "open", "high", "low", "close"}
        if not required.issubset(fields):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for line, row in enumerate(reader, 2):
            ts = parse_utc(row[time_col].strip())
            values = [float(row[k]) for k in ("open", "high", "low", "close")]
            if not all(math.isfinite(x) and x > 0 for x in values):
                raise ValueError(f"Invalid OHLC at CSV line {line}")
            o, h, l, c = values
            if h < max(o, l, c) or l > min(o, h, c):
                raise ValueError(f"Invalid OHLC ordering at CSV line {line}")
            bar = Bar(ts, o, h, l, c)
            if ts in parsed and parsed[ts] != bar:
                raise ValueError(f"Conflicting duplicate timestamp: {ts.isoformat()}")
            parsed[ts] = bar
    return [parsed[t] for t in sorted(parsed)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_or_create_state(path: Path, requested_start: str | None) -> dict:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        saved_start = parse_utc(state["forward_start"])
        if requested_start and parse_utc(requested_start) != saved_start:
            raise SystemExit(
                f"Forward boundary is already frozen at {saved_start.isoformat()}; "
                "refusing to change it. Use the existing state file."
            )
        return state
    start = parse_utc(requested_start) if requested_start else next_m5_boundary(utc_now())
    state = {
        "forward_start": start.isoformat(),
        "created_at_utc": utc_now().isoformat(),
        "recorded_trade_keys": [],
        "last_data_sha256": None,
        "last_latest_m1_utc": None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(path)
    return state


def append_trade_rows(path: Path, trades: list[dict]) -> None:
    fields = ["signal_time_utc", "entry_time_utc", "settlement_time_utc",
              "outcome", "profit_92", "adx", "atr_ratio", "momentum3"]
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        for t in trades:
            writer.writerow({
                "signal_time_utc": t["signal_time"].isoformat(),
                "entry_time_utc": t["entry_time"].isoformat(),
                "settlement_time_utc": t["settlement_time"].isoformat(),
                "outcome": t["outcome"],
                "profit_92": f'{t["profit"]:.2f}',
                "adx": f'{t["adx"]:.6f}',
                "atr_ratio": f'{t["atr_ratio"]:.10f}',
                "momentum3": f'{t["momentum3"]:.8f}',
            })
        f.flush()


def save_state(path: Path, state: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True,
                    help="Live M1 CSV appended by the EURUSD guest-feed collector")
    ap.add_argument("--poll-seconds", type=int, default=15)
    ap.add_argument("--max-age-seconds", type=int, default=180)
    ap.add_argument("--forward-start", default=None,
                    help="Optional UTC ISO timestamp; only accepted on first launch")
    ap.add_argument("--state", type=Path, default=None)
    ap.add_argument("--ledger", type=Path, default=None)
    args = ap.parse_args()
    if args.poll_seconds < 5 or args.max_age_seconds < 60:
        raise SystemExit("poll-seconds must be >=5 and max-age-seconds >=60")
    state_path = args.state or args.data.parent / "hydra_put_forward_state.json"
    ledger_path = args.ledger or args.data.parent / "hydra_put_forward_trades.csv"
    state = load_or_create_state(state_path, args.forward_start)
    forward_start = parse_utc(state["forward_start"])

    print("=" * 68)
    print("HYDRA — FROZEN PUT FORWARD MONITOR | RESEARCH ONLY | NO TRADING")
    print(f"Data: {args.data}")
    print(f"Forward boundary (frozen): {forward_start.isoformat()}")
    print(f"Ledger: {ledger_path}")
    print("Stop with Ctrl+C. Do not edit thresholds during collection.")
    print("=" * 68)

    while True:
        try:
            if not args.data.exists():
                print(f"[WAIT] Data file not found: {args.data}")
                time.sleep(args.poll_seconds)
                continue
            m1 = load_m1(args.data)
            if not m1:
                print("[WAIT] No M1 rows yet")
                time.sleep(args.poll_seconds)
                continue
            now = utc_now()
            latest = m1[-1].timestamp
            age = (now - latest).total_seconds()
            digest = sha256_file(args.data)
            segments = make_m5(m1)
            bars_count = sum(len(s) for s in segments)
            all_trades = [t for t in build_candidate(segments)
                          if t["signal_time"] >= forward_start]
            # Never score a trade until its expiry candle is complete and
            # the market-data timestamp is fresh enough to trust.
            eligible = [t for t in all_trades
                        if t["settlement_time"] <= now - timedelta(seconds=10)]
            keys = set(state.get("recorded_trade_keys", []))
            fresh = -60 <= age <= args.max_age_seconds
            new_trades = []
            if fresh:
                for trade in eligible:
                    key = trade["signal_time"].isoformat()
                    if key not in keys:
                        new_trades.append(trade)
                        keys.add(key)
            if new_trades:
                append_trade_rows(ledger_path, new_trades)
                state["recorded_trade_keys"] = sorted(keys)
            state["last_data_sha256"] = digest
            state["last_latest_m1_utc"] = latest.isoformat()
            state["last_check_utc"] = now.isoformat()
            state["last_data_age_seconds"] = round(age, 1)
            state["recorded_decisive"] = sum(
                1 for t in eligible if t["outcome"] != "DRAW"
                and t["signal_time"].isoformat() in keys
            )
            state["recorded_wins"] = sum(
                1 for t in eligible if t["outcome"] == "WIN"
                and t["signal_time"].isoformat() in keys
            )
            state["recorded_losses"] = sum(
                1 for t in eligible if t["outcome"] == "LOSS"
                and t["signal_time"].isoformat() in keys
            )
            state["recorded_draws"] = sum(
                1 for t in eligible if t["outcome"] == "DRAW"
                and t["signal_time"].isoformat() in keys
            )
            save_state(state_path, state)
            status = "FRESH" if fresh else f"STALE ({age:.0f}s)"
            decisive = state["recorded_decisive"]
            wins = state["recorded_wins"]
            wr = 100.0 * wins / decisive if decisive else 0.0
            net = 0.92 * wins - state["recorded_losses"]
            ci = wilson_interval(wins, decisive)
            ci_text = f"{100.0 * ci[0]:.2f}–{100.0 * ci[1]:.2f}%" if ci else "n/a"
            print(
                f"[{now.isoformat(timespec='seconds')}] {status} | "
                f"M1={len(m1)} M5={bars_count} segments={len(segments)} | "
                f"new trades={len(new_trades)} | "
                f"forward W/L/D={state['recorded_wins']}/"
                f"{state['recorded_losses']}/{state['recorded_draws']} | "
                f"WR={wr:.2f}% CI95={ci_text} net={net:.2f} | sha256={digest[:12]}"
            )
            if not fresh:
                print("[HOLD] No outcomes recorded until the feed is fresh.")
        except KeyboardInterrupt:
            print("\nPUT monitor stopped. State and ledger preserved.")
            break
        except Exception as exc:
            print(f"[ERROR] {type(exc).__name__}: {exc}")
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
