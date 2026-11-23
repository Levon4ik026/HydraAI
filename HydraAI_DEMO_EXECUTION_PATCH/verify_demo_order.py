from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from hydra_demo.pocket_option_demo import PocketOptionDemoAdapter

BASE = Path(__file__).resolve().parent
VERIFICATION_PATH = BASE / "observer_data" / "demo_order_adapter_verified.json"


async def main() -> int:
    if os.name != "nt":
        print("ERROR: run this verification on Windows.")
        return 2

    os.environ["HYDRA_ACCOUNT_MODE"] = "DEMO"
    os.environ["HYDRA_INSTRUMENT"] = "EURUSD"
    os.environ["HYDRA_ALLOW_OTC"] = "0"

    adapter = PocketOptionDemoAdapter(amount=1)
    try:
        await adapter.connect()
        snapshot = None
        for _ in range(80):
            snapshot = await adapter.get_market_snapshot()
            if snapshot.get("status") not in {"UNKNOWN", "STALE"}:
                break
            await asyncio.sleep(0.25)

        print("MARKET_SNAPSHOT=" + json.dumps(snapshot, ensure_ascii=False))
        if not snapshot or snapshot.get("status") != "ACTIVE":
            print("BLOCKED: EURUSD must be active, non-OTC and have a live payout >=92%. No order was sent.")
            return 3
        if snapshot.get("symbol") != "EURUSD" or snapshot.get("is_otc") is not False:
            print("BLOCKED: broker metadata does not positively confirm non-OTC EURUSD. No order was sent.")
            return 3
        if snapshot.get("active") is not True:
            print("BLOCKED: EURUSD is not confirmed active. No order was sent.")
            return 3
        payout = snapshot.get("payout_ratio")
        if not isinstance(payout, (int, float)) or not 0.92 <= payout <= 1:
            print("BLOCKED: live payout is missing, invalid or below 92%. No order was sent.")
            return 3
        if not isinstance(snapshot.get("metadata_age_seconds"), (int, float)) or snapshot["metadata_age_seconds"] > 45:
            print("BLOCKED: broker asset metadata is stale or unverified. No order was sent.")
            return 3
        if 300 not in snapshot.get("timeframes_seconds", []):
            print("BLOCKED: Pocket Option does not currently advertise 300-second expiry. No order was sent.")
            return 4

        direction = input("Choose direction for ONE verification trade (CALL/PUT): ").strip().upper()
        if direction not in {"CALL", "PUT"}:
            print("Cancelled: direction must be CALL or PUT. No order was sent.")
            return 5
        confirmation = input(
            f"Open ONE DEMO EURUSD {direction} trade, stake=1, expiry=5 minutes? Type YES to confirm: "
        ).strip()
        if confirmation != "YES":
            print("Cancelled. No order was sent.")
            return 0

        os.environ["HYDRA_DEMO_AUTOTRADE"] = "1"
        result = await adapter.open_and_wait(direction, 5, payout=None)
        if not result.get("closed") or not result.get("deal_id") or not result.get("is_demo"):
            raise RuntimeError("broker did not confirm a closed DEMO deal")

        record = {
            "status": "VERIFIED",
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "deal_id": result["deal_id"],
            "asset": "EURUSD",
            "is_demo": True,
            "closed": True,
            "amount": 1,
            "expiry_seconds": 300,
            "direction": direction,
            "profit": result.get("profit", ""),
            "close_price": result.get("close_price", ""),
        }
        VERIFICATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = VERIFICATION_PATH.with_suffix(".json.tmp")
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(VERIFICATION_PATH)
        print("VERIFICATION_STATUS=VERIFIED")
        print("DEAL_ID=" + str(result["deal_id"]))
        print("SENTINEL=" + str(VERIFICATION_PATH))
        return 0
    except Exception as exc:
        print(f"VERIFICATION_STATUS=FAILED: {type(exc).__name__}: {exc}")
        print("If order submission may have timed out, inspect Pocket Option history manually. Do not retry blindly.")
        return 6
    finally:
        try:
            await adapter.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
