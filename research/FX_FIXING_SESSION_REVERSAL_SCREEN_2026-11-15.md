# FX fixing and NY-session reversal screen — run 1 (2026-11-15)

## Scope
Five frozen M1 BID hypotheses were tested in GitHub Actions run [43692329272](https://github.com/Levon4ik026/HydraAI/actions/runs/43692329272). Code and report are isolated to hydra/research-validation. The screen used Dukascopy EUR/USD M1 BID from 2024-01-01 22:00 UTC through 2026-11-13 21:59 UTC.

Full report: ../research-artifacts/fixing-reversal-discovery/report.md  
Manifest: ../research-artifacts/fixing-reversal-discovery/manifest.json  
Trade ledger: ../research-artifacts/fixing-reversal-discovery/trades.csv  
Protocol: ../research-artifacts/fixing-reversal-discovery-protocol-v1.md

## Data integrity
- 1,068,882 raw and valid unique M1 rows; invalid 0; duplicate timestamps 0.
- 3,643 gap intervals; 438,798 missing minutes; largest missing interval 2,944 minutes. The aggregate gap count includes normal weekend/market closures and must not be interpreted as 438,798 unexpected data errors.
- Raw CSV SHA-256: 1ab0157ed2507ce4e62bede90376736dbbe8ec271b0543e28752f37a1d7229f4
- Chronological calendar split: TRAIN before 2025-09-20; VALIDATION 2025-09-20 through 2026-04-16; TEST from 2026-04-17. Historical TEST is not pristine because this underlying source period has been examined in prior HydraAI screens.

## Results at 92% payout

| Hypothesis | N | W/L/D | WR | Net | VALIDATION | TEST | Decision |
|---|---:|---|---:|---:|---|---|---|
| Tokyo adaptive pre-fix fade, 4h, 60m | 49 | 25/23/1 | 52.08% | +0.00u | 9 trades, 12.50%, -6.08u | 3 trades, 33.33%, -1.08u | Insufficient |
| ECB adaptive pre-fix fade, 07:00–14:15 Berlin, 60m | 701 | 338/360/3 | 48.42% | -49.04u | 141, 46.10%, -16.20u | 147, 44.52%, -21.20u | Failed |
| London adaptive pre-fix fade, 07:00–16:00 London, 60m | 729 | 384/341/4 | 52.97% | +12.28u | 144, 55.94%, +10.60u | 150, 48.67%, -9.84u | Failed stability |
| NY 17:00 daily shock fade, 1.5x prior-20 mean, 60m | 36 | 26/10/0 | 72.22% | +13.92u | 10, 50.00%, -0.40u | 2, 50.00%, -0.08u | Insufficient |
| NY Sunday–Friday weekly shock fade, 1.0x prior-13 mean, 60m | 9 | 3/6/0 | 33.33% | -3.24u | 4, 25.00%, -2.08u | 0 trades | Failed / insufficient |

## Interpretation
- **No candidate passed the preregistered primary screen.** The batch counter remains 0/5; no candidate should be sent as a qualified lead.
- The 72.22% daily-shock result is the highest WR observed, but it is only 36 trades and the later splits contain 10 and 2 trades, both at 50% with negative net. It is a research clue, not a candidate confirmation. The day-cluster bootstrap on the pooled historical sample is not a substitute for later-split sample size.
- London fixing fade has positive pooled and VALIDATION results, but TEST is 48.67% with -9.84u; do not promote it.
- ECB fixing fade is negative in both VALIDATION and TEST.
- Tokyo's 4-hour pre-window yielded only 49 eligible windows because it crosses the New York rollover/closure on many dates. Do not repair this rule after seeing results. A separately preregistered Tokyo window matching the paper's 17:00 New York pre-fix start can be evaluated as a new rule.
- The first screen tested an **adaptive fade of the observed pre-fix EUR/USD move**. It did not test the paper's more direct directional implication (USD tends to strengthen before the fix and weaken after it, implying EUR/USD CALL after the fix on days with a negative pre-fix EUR/USD move). That is a distinct, still-untested hypothesis and is the next research family.
- NY daily/weekly session completeness was low under the strict 17:00–17:00 / 99% rule (daily: 131 eligible windows; weekly: 19). A new protocol may define sessions excluding the known New York rollover interval, but it must be frozen before evaluating its outcomes.

## Next research direction
Preregister the direct post-fixing EUR/USD CALL hypothesis, with:
- Tokyo pre-window from prior-day 17:00 America/New_York to 09:55 Asia/Tokyo;
- ECB pre-window 07:00–14:15 Europe/Berlin;
- London pre-window 07:00–16:00 Europe/London;
- CALL only when the completed pre-fix EUR/USD return is negative; otherwise WAIT;
- expiry selected on TRAIN only from a fixed 5/10/15/20/30/60-minute grid, then frozen before VALIDATION/TEST;
- matched PUT controls at identical timestamps;
- a separate NY session shock study using a rollover-excluded session definition and explicit daily/weekly coverage diagnostics.

No real trades, OTC instruments, or auto-trading were used.
