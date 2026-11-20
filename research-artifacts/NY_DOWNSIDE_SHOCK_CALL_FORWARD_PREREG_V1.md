# NY downside-shock CALL asymmetry — forward-only preregistration v1

Frozen: 2026-11-15
Branch: hydra/research-validation
Status: hypothesis generated from an exploratory historical direction split; NOT a qualified strategy.

## Discovery context (post-hoc; not confirmatory)
The prior five-family screen (run 43693122310) reported the NY rollover-excluded daily shock fade pooled across directions. Its selected expiry was 30 minutes, selected using TRAIN only for the pooled two-sided rule. A post-hoc split of those same 30-minute trades by the direction of the completed NY session showed:

| Split | CALL after negative session: N, W/L/D, WR, net @92% | PUT after positive session: N, W/L/D, WR, net @92% |
|---|---|---|
| TRAIN | 32, 22/10/0, 68.75%, +10.24u | 39, 14/23/2, 37.84%, -10.12u |
| VALIDATION | 17, 11/6/0, 64.71%, +4.12u | 17, 6/11/0, 35.29%, -5.48u |
| TEST | 13, 9/4/0, 69.23%, +4.28u | 7, 2/5/0, 28.57%, -3.16u |
| Pooled | 62, 42/20/0, 67.74%, +18.64u | 63, 22/39/2, 36.07%, -18.76u |

This split was inspected after seeing the pooled screen. It is exploratory, subject to multiple-testing/selection bias, and must not be presented as an independent discovery or as proof of an edge. The small TEST subgroup (13 trades) is particularly weak evidence. No strategy is promoted.

## Frozen forward-only hypothesis
- Instrument: EUR/USD only; Dukascopy M1 BID for research.
- Session: completed 18:00 America/New_York to 17:00 next local calendar day, starting Sunday through Thursday; exclude the 17:00–18:00 rollover.
- Session quality: exact start and end-1-minute bars; at least 99% minute coverage; no within-session gap greater than 5 minutes.
- Shock threshold: after 20 preceding valid sessions, current session log return must be <= negative 1.0x the mean absolute log return of those 20 preceding valid sessions (current session excluded).
- Signal: CALL only, at the next 18:00 America/New_York session open. Otherwise WAIT. No PUT signals.
- Expiry: fixed 30 minutes. This is carried forward from the pooled TRAIN-only selection in the original protocol; do not reselect it using this forward sample.
- Entry: exact M1 open at the next session start; settlement: close of the M1 bar timestamped entry+29 minutes. Missing required bars exclude the event.
- Payout: WIN +0.92u, LOSS -1u, DRAW 0u. Also report payout sensitivity.
- Comparator: matched PUT at the exact same timestamps/prices, clearly secondary.
- Forward start: first eligible session signal whose entry time is strictly after 2026-11-13T21:59:00Z, the latest source-data timestamp in the discovery run.
- No reuse of historical observations for promotion. The historical TRAIN/VALIDATION/TEST split is discovery context only, not confirmation.

## Promotion gates
- Do not make any parameter, threshold, direction, expiry, session, or filter changes after forward monitoring starts.
- Minimum 100 forward trades before considering statistical review; report W/L/D, decisive WR, Wilson 95% interval, net/ROI/expectancy at actual payout, PF, max drawdown, max loss streak, active days, monthly/quarterly stability, and day-cluster bootstrap.
- Require positive net at 92% and WR above 52.0833% in the forward sample; the lower confidence bound and dependence-aware uncertainty must also be discussed. A nominal pass is only a lead, not live-trading approval.
- Compare live Pocket Option DEMO executable quotes, payout, timing and settlement before any practical use. No real trades, OTC instruments, or auto-trading.
- If fewer than 100 forward trades, report as insufficient sample and continue unchanged. Never fill a five-candidate batch with this single under-sampled hypothesis.

## Execution log

- 2026-11-20: requested a fresh forward-only audit after the latest completed UTC session became available. This entry is operational only; the frozen signal rule, cutoff, session definition, 30-minute expiry, direction, payout accounting, and promotion gates are unchanged.
