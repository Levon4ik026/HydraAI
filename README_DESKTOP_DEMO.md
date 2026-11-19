# HydraAI desktop DEMO integration — first safe increment

This branch adds an isolated observation/risk-gate package. It does **not** claim to place Pocket Option orders.

## What is included
- hydra_demo/candidate_registry.json: five candidate definitions and their previously reported train/validation/test figures, preserving their current research status.
- hydra_demo/engine.py: CSV loader, OHLC validation, duplicate timestamp suppression, stale/gap detection, strict M5 aggregation, EMA/RSI helpers, a conservative CAND-001 signal evaluator, and a fail-closed execution gate.
- tests/test_engine.py: deterministic unit tests.

## Critical status
All candidates remain shadow_only or research_only. Historical percentages are not live performance. CAND-008/010/012/014 do not meet the stated held-out evidence threshold; CAND-014 has only 62 pooled historical trades and no eligible forward trades in the reviewed window.

**Automatic Pocket Option DEMO execution is not enabled.** The reviewed desktop source archive does not provide a verified, supported order adapter in the active source tree. The guest WebSocket feed is an observation feed, not proof of an order API. DemoExecutionGate rejects execution unless a verified broker adapter is explicitly supplied. No REAL account path is enabled; no OTC; no martingale.

## Integration notes
The package is deliberately isolated because the GitHub main branch does not contain the desktop GUI source (main.py) that exists in the user's local archive. It must be wired into that desktop app after source reconciliation. Do not overwrite the local app with this branch as if it were a complete release.

Expected source CSV columns: datetime_utc,open,high,low,close. The current guest feed file is expected at observer_data/eurusd_guest_candles.csv.

## Run tests
From repository root:
python -m unittest discover -s tests -v

## Before any DEMO order integration
1. Obtain a supported and verifiable Pocket Option DEMO order interface and confirm its permitted use.
2. Add adapter-specific tests using a demo-only account and an explicit order confirmation/result.
3. Forward-observe candidates on fresh, continuous guest-feed data; log payout per opportunity and actual expiry outcome.
4. Require minimum sample, positive expectancy at observed payout, drawdown and stability across time blocks before promoting a candidate.
