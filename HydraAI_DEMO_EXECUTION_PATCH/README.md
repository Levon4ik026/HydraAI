# HydraAI DEMO execution patch

Separate patch package. Existing research branch and original C:\HydraAI_Desktop are not modified.

## Included changes
- Connects the existing five-candidate forward monitor to the first live M1 candle after a completed M5 trigger.
- Uses completed candles for regime classification and outcome scoring; live M1 is only the next-minute entry reference.
- Runs broker I/O in a separate worker process, not in the PySide6 GUI thread.
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
.\.venv\Scripts\python.exe -m py_compile .\main.py .\demo_execution_worker.py .\hydra_demo\engine.py .\hydra_demo\adaptive.py .\hydra_demo\runtime.py .\hydra_demo\pocket_option_demo.py

.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_execution_gate.py" -v

The GUI button DEMO AUTO is OFF by default. It requires a separate confirmation and a fresh connected feed.

For EXE distribution:
.\.venv\Scripts\pyinstaller.exe --clean --noconfirm .\HydraDemoExecution.spec
The worker EXE must be at HydraDemoExecution\HydraDemoExecution.exe under the HydraAI distribution root.

## Expiry caveat
The previous closed-market diagnostic reported EURUSD timeframes [60, 120, 180, 300] seconds. That does not establish availability of 30- or 60-minute expiries. The worker rejects any expiry absent from current live metadata. With that reported list, five-minute candidates may pass; 30- and 60-minute candidates are blocked until the broker actually advertises those durations.

## Release status
Integration candidate, not a claim that live-market order execution has already been tested. First run compile/tests, then connect while EURUSD is open and confirm worker reports READY with market.status=ACTIVE, payout_percent >= 92 and intended expiry present. Do not enable DEMO auto execution before those checks.
