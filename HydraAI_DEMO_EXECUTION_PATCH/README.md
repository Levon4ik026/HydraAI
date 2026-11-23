# HydraAI DEMO execution patch

Separate patch package. Existing research branch and original C:\HydraAI_Desktop are not modified.

## Included changes
- Connects the existing five-candidate forward monitor to the first live M1 candle after a completed M5 trigger.
- Uses completed candles for regime classification and outcome scoring; live M1 is only the next-minute entry reference.
- Runs broker I/O in a separate worker process, not in the PySide6 GUI thread.
- Strategy selection is filtered by the live expiry durations Pocket Option currently advertises; unsupported 30/60-minute candidates are not selected for execution.
- Reads EURUSD metadata from Pocket Option updateAssets. Metadata is trusted only when that event was seen within 45 seconds.
- Checks active status, EURUSD identity, non-OTC, live payout >= 92%, and broker-listed expiry.
- Fixed stake 1, one unresolved position at a time, no martingale, no blind retry.
- Persists signal IDs before submission; uncertain orders halt and require manual broker-history review.
- Daily loss stop: 3 stake units. REAL and OTC are rejected.

## Copy into the experimental project
Target: C:\HydraAI_ADAPTIVE_DEMO\HydraAI_CURRENT_INTEGRATED

Copy each file into the matching destination:
- main.py -> project root main.py
- demo_execution_worker.py -> project root
- verify_demo_order.py -> project root
- HydraDemoExecution.spec -> project root
- hydra_demo\engine.py -> hydra_demo\engine.py
- hydra_demo\adaptive.py -> hydra_demo\adaptive.py
- hydra_demo\runtime.py -> hydra_demo\runtime.py
- hydra_demo\pocket_option_demo.py -> hydra_demo\pocket_option_demo.py
- hydra_demo\__init__.py -> hydra_demo\__init__.py
- tests\test_execution_gate.py -> tests\test_execution_gate.py

Back up destination files first. Do not copy over C:\HydraAI_Desktop.

## Verify before enabling
PowerShell from the experimental project:
.\.venv\Scripts\python.exe -m py_compile .\main.py .\demo_execution_worker.py .\verify_demo_order.py .\hydra_demo\engine.py .\hydra_demo\adaptive.py .\hydra_demo\runtime.py .\hydra_demo\pocket_option_demo.py

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_execution_gate.py" -v

The GUI button DEMO AUTO is OFF by default. It requires a separate confirmation, a fresh connected feed, and a verification record created by verify_demo_order.py.

Before automatic execution, run this once while EURUSD is open and the live payout is at least 92%:

.\.venv\Scripts\python.exe .\verify_demo_order.py

The script prompts for CALL or PUT and asks you to type YES before sending exactly one 1-unit, 5-minute DEMO EURUSD order. It writes observer_data\\demo_order_adapter_verified.json only after the SDK returns the matching DEMO EURUSD deal with a non-empty close timestamp. If the order result is uncertain, no verification record is written and automatic execution remains locked.

For EXE distribution:
.\.venv\Scripts\pyinstaller.exe --clean --noconfirm .\HydraDemoExecution.spec
The worker EXE must be at HydraDemoExecution\HydraDemoExecution.exe under the HydraAI distribution root.

## Expiry caveat
The previous closed-market diagnostic reported EURUSD timeframes [60, 120, 180, 300] seconds. That does not establish availability of 30- or 60-minute expiries. The worker rejects any expiry absent from current live metadata. With that reported list, five-minute candidates may pass; 30- and 60-minute candidates are blocked until the broker actually advertises those durations.

## Release status — not yet approved for automatic DEMO trading

Source-level safety tests pass, but the following release blockers remain:

- CAND-010 is the previously agreed Previous UTC-day low breakdown: a completed M5 candle crosses the prior UTC-day low from above; direction PUT; expiry 60 minutes. A regression test should preserve this exact rule.
- The adaptive selector requires at least 100 forward outcomes per candidate in the matching regime, positive expectancy, a 95% Wilson lower bound above break-even, and drawdown <= 3 units. The patch does not include a validated seed-statistics file, so a fresh install will remain WAIT until enough forward data has accumulated.
- CAND-008 uses 30-minute expiry and CAND-010 uses 60-minute expiry. The user confirmed both durations are available in Pocket Option. Keep a runtime expiry check as a final safeguard.
- This repository folder is an overlay patch, not a complete standalone HydraAI distribution. The target integrated project must already contain its base GUI/feed modules and dependencies.
- Broker connectivity, account-wide open-position refresh, the explicit one-trade verification, and a Windows EXE build have not been exercised in the user's DEMO environment.

Do not run verify_demo_order.py or enable DEMO auto execution until the strategy-rule blockers and the broker/Windows checks above are resolved. REAL and OTC remain prohibited.
