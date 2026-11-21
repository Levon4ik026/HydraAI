"""Pocket Option DEMO adapter based on the user's successful order test.

Fail-closed: DEMO + EURUSD only, no OTC, no REAL mode, no automatic retries.
The adapter uses MemoryDealsStorage(client), exactly as in hydra_demo_order_test.py.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal

SERVICE = "HydraAI-PocketOption-DEMO"


class DemoAdapterError(RuntimeError):
    pass


class PocketOptionDemoAdapter:
    def __init__(self, amount: int = 1):
        if isinstance(amount, bool) or int(amount) != amount or amount <= 0:
            raise ValueError("DEMO stake must be a positive whole number")
        self.amount = int(amount)
        self.client = None
        self.storage = None
        self.assets = None
        self._asset_update_at = None
        self._connected = False
        self._position_unresolved = False
        self._order_lock = asyncio.Lock()

    async def connect(self):
        if os.name != "nt":
            raise DemoAdapterError("DEMO adapter is supported only on Windows")

        if os.getenv("HYDRA_ACCOUNT_MODE", "DEMO").upper() != "DEMO":
            raise DemoAdapterError("REAL account mode is rejected")
        if os.getenv("HYDRA_INSTRUMENT", "EURUSD").upper() != "EURUSD":
            raise DemoAdapterError("only EURUSD is allowed")
        if os.getenv("HYDRA_ALLOW_OTC", "0") != "0":
            raise DemoAdapterError("OTC is prohibited")

        try:
            import keyring
            from pocket_option import PocketOptionClient
            from pocket_option.constants import Regions
            from pocket_option.middlewares import MakeJsonOnMiddleware, FixTypesMiddleware
            from pocket_option.models import AuthorizationData, Asset
            from pocket_option.contrib.deals import MemoryDealsStorage
            from pocket_option.contrib.assets import MemoryAssetsStorage
        except Exception as exc:
            raise DemoAdapterError(f"Pocket Option SDK/dependencies unavailable: {type(exc).__name__}: {exc}") from exc

        session = keyring.get_password(SERVICE, "session")
        uid_text = keyring.get_password(SERVICE, "uid")
        if not session or not uid_text:
            raise DemoAdapterError("DEMO credentials not found in Windows Credential Manager")
        try:
            uid = int(uid_text)
        except (TypeError, ValueError) as exc:
            raise DemoAdapterError("stored DEMO UID is invalid") from exc
        if uid <= 0:
            raise DemoAdapterError("stored DEMO UID must be positive")

        authorization = AuthorizationData(
            session=session,
            is_demo=1,
            uid=uid,
            platform=2,
            is_fast_history=True,
            is_optimized=True,
        )
        client = PocketOptionClient(
            middlewares=[MakeJsonOnMiddleware(), FixTypesMiddleware()],
            reconnection=False,
            logger=False,
            handle_sigint=False,
        )

        async def on_connect():
            await client.emit.auth(authorization)

        client.on.connect(on_connect)
        assets = MemoryAssetsStorage(client)

        async def on_assets_update(_items):
            self._asset_update_at = datetime.now(timezone.utc)

        client.on.assets_update(on_assets_update)
        try:
            await client.connect(url=Regions.DEMO, wait=True, wait_timeout=10, retry=False)
            await client.wait_for_authorization(timeout=30)
            if not client.is_authorized:
                raise DemoAdapterError("DEMO authorization was not confirmed")
            # Same construction/order as the user's proven test script.
            storage = MemoryDealsStorage(client)
        except Exception:
            try:
                await client.disconnect()
            finally:
                raise

        self.client = client
        self.storage = storage
        self.assets = assets
        self._connected = True
        return True

    async def get_market_snapshot(self):
        """Return broker metadata only when updateAssets was observed recently."""
        from pocket_option.models import Asset
        if not self._connected or self.assets is None:
            return {"status": "DISCONNECTED", "reason": "adapter is not connected"}
        if self._asset_update_at is None:
            return {"status": "UNKNOWN", "reason": "no updateAssets event received"}
        now = datetime.now(timezone.utc)
        age = (now - self._asset_update_at).total_seconds()
        if age < -2 or age > 45:
            return {"status": "STALE", "reason": f"asset metadata age {age:.1f}s"}
        item = await self.assets.get_asset(assset=Asset.EURUSD)
        if item is None:
            return {"status": "UNKNOWN", "reason": "EURUSD missing from updateAssets"}
        try:
            payout_percent = int(item.payout)
            timeframes = sorted({int(x.time) for x in (item.timeframes or [])})
        except (TypeError, ValueError, AttributeError) as exc:
            return {"status": "UNKNOWN", "reason": f"invalid EURUSD metadata: {exc}"}
        identity_ok = getattr(item, "asset", None) == Asset.EURUSD
        is_otc = bool(getattr(item, "is_otc", True))
        active = bool(getattr(item, "active", False))
        if not identity_ok or is_otc:
            status, reason = "REJECTED", "asset identity mismatch or OTC instrument"
        elif not active:
            status, reason = "MARKET_CLOSED", "EURUSD is currently inactive"
        elif not 0 <= payout_percent <= 100:
            status, reason = "REJECTED", "invalid payout percentage"
        elif payout_percent < 92:
            status, reason = "LOW_PAYOUT", f"live payout {payout_percent}% is below 92%"
        else:
            status, reason = "ACTIVE", "live EURUSD metadata passed"
        return {
            "status": status, "reason": reason, "symbol": "EURUSD",
            "active": active, "is_otc": is_otc,
            "payout_percent": payout_percent, "payout_ratio": payout_percent / 100.0,
            "timeframes_seconds": timeframes, "metadata_age_seconds": round(age, 2),
            "updated_at": self._asset_update_at.isoformat(),
        }

    async def open_and_wait(self, direction: str, expiry_minutes: int, payout: float | None = None):
        if os.getenv("HYDRA_DEMO_AUTOTRADE") != "1":
            raise DemoAdapterError("orders disabled: explicit HYDRA_DEMO_AUTOTRADE=1 is required")
        if not self._connected or self.client is None or self.storage is None:
            raise DemoAdapterError("adapter is not connected")
        if direction not in {"CALL", "PUT"}:
            raise DemoAdapterError("direction must be CALL or PUT")
        if expiry_minutes not in {5, 30, 60}:
            raise DemoAdapterError("expiry must be 5, 30 or 60 minutes")
        snapshot = await self.get_market_snapshot()
        if snapshot.get("status") != "ACTIVE":
            raise DemoAdapterError(f"live market gate rejected order: {snapshot.get('status')} / {snapshot.get('reason')}")
        payout = Decimal(str(snapshot["payout_ratio"]))
        if payout < Decimal("0.92") or payout > Decimal("1"):
            raise DemoAdapterError("actual live payout is below 92% or invalid")
        if expiry_minutes * 60 not in snapshot.get("timeframes_seconds", []):
            raise DemoAdapterError(
                f"expiry {expiry_minutes * 60}s is not offered by EURUSD; "
                f"available={snapshot.get('timeframes_seconds', [])}"
            )

        async with self._order_lock:
            if self._position_unresolved:
                raise DemoAdapterError("previous trade unresolved; one-position lock remains engaged")

            from pocket_option.models import Asset, DealAction
            action = DealAction.CALL if direction == "CALL" else DealAction.PUT
            # Set before submit. A timeout can mean the server accepted the order;
            # never retry blindly and never release the lock without confirmed close.
            self._position_unresolved = True
            try:
                deal = await self.storage.open_deal(
                    asset=Asset.EURUSD,
                    amount=self.amount,
                    action=action,
                    time=expiry_minutes * 60,
                    is_demo=1,
                )
            except Exception as exc:
                raise DemoAdapterError(
                    "order submission failed or was ambiguous; automatic retry is prohibited; "
                    "check Pocket Option trade history manually"
                ) from exc

            if getattr(deal, "is_demo", None) not in (1, True):
                raise DemoAdapterError("broker response did not confirm DEMO mode; lock remains engaged")
            if getattr(deal, "asset", None) not in (Asset.EURUSD, "EURUSD"):
                raise DemoAdapterError("broker response asset mismatch; lock remains engaged")

            try:
                result = await self.storage.check_deal_result(
                    wait_time=expiry_minutes * 60 + 120,
                    deal=deal,
                )
            except Exception as exc:
                raise DemoAdapterError(
                    f"trade {getattr(deal, 'id', 'unknown')} was accepted but closure is unconfirmed; "
                    "lock remains engaged"
                ) from exc

            # check_deal_result() returns the closed deal according to SDK contract.
            if getattr(result, "id", None) != getattr(deal, "id", None):
                raise DemoAdapterError(
                    "returned deal ID mismatch; lock remains engaged"
                )

            if getattr(result, "is_demo", None) not in (1, True):
                raise DemoAdapterError(
                    "closed deal is not confirmed as DEMO; lock remains engaged"
                )

            if getattr(result, "asset", None) not in (Asset.EURUSD, "EURUSD"):
                raise DemoAdapterError(
                    "closed deal asset mismatch; lock remains engaged"
                )

            self._position_unresolved = False
            return {
                "deal_id": str(getattr(deal, "id", "")),
                "direction": direction,
                "asset": "EURUSD",
                "amount": self.amount,
                "is_demo": True,
                "closed": True,
                "profit": str(getattr(result, "profit", "")),
                "close_price": str(getattr(result, "close_price", "")),
            }

    async def disconnect(self):
        if self.client is not None:
            await self.client.disconnect()
        self._connected = False
        self.client = None
        self.storage = None
        self.assets = None
        self._asset_update_at = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *_):
        await self.disconnect()