# RSI bad-signal exact inversion — original vs inverse (2026-11-09)

## Core result

We recovered the original cohort construction and reproduced the exact historical trade list for the weak original direction. This is the closest direct test so far of the user's hypothesis: identify a rule that is consistently wrong, then invert its direction on the identical entries and expiries.

Frozen Candidate A:
- Completed M1 RSI(14) crosses down through 30.
- Signal candle geometric upper wick <= 0.1 pip: `(high - max(open, close))/0.0001 <= 0.1`.
- Original direction: PUT.
- Inverse direction: CALL.
- Entry: next M1 open.
- Expiry: close of the 15th entry candle.
- Shared one-position lockout is formed across BOTH RSI crossing directions before applying the wick condition.
- The inverse is calculated on the exact same entry and expiry prices; no rescheduling or cherry-picking is allowed.

## Original vs inverse — identical trade cohort

| Split | Trades | Original W/L/D | Original WR | Original net @92% | Inverse W/L/D | Inverse WR | Inverse net @92% |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,278 | 548/712/18 | 43.49% | -207.84u | 712/548/18 | 56.51% | +107.04u |
| VALIDATION | 340 | 156/178/6 | 46.70% | -34.48u | 178/156/6 | 53.29% | +7.76u |
| TEST | 312 | 120/181/11 | 39.87% | -70.60u | 181/120/11 | 60.13% | +46.52u |
| TOTAL | 1,930 | 824/1,071/35 | 43.49% | -312.92u | 1,071/824/35 | 56.52% | +161.32u |

Win rates exclude draws. Net assumes a constant 92% payout, +0.92 per win, -1 per loss and 0 for a draw. The original and inverse results are exact complements, so this table is one cohort, not two independent tests.

## What this says

1. **The original direction is genuinely poor on this cohort:** below 50% decisive accuracy in all three chronological splits, and 39.87% on TEST.
2. **The exact inverse is positive in all three splits:** 56.51%, 53.29%, and 60.13%.
3. The inverse is not merely benefiting from a lucky aggregate split: the original direction is below 50% in each split. However, validation's inverse margin is modest (+7.76 units).
4. This supports the mechanism worth investigating: some indicator/context combinations may encode a systematically adverse directional bias, and exact inversion can reveal it.
5. It does **not** establish a general law that every bad strategy becomes profitable when reversed. This candidate was selected from a broad feature screen, so selection bias remains, and TEST has already been examined.

## Reproducibility and correction history

Canonical script: `research/rsi_shared_schedule_reproduction.py`. It verifies the dataset SHA-256, builds the shared schedule across both RSI directions, stores original and inverse outcomes per identical trade, and writes a row-level CSV ledger.

The prior false withdrawal of Candidate A is superseded by `RSI_SHARED_SCHEDULE_RECOVERY_CORRECTION_2026-11-09.md`. The mistake was using high-to-close distance instead of geometric upper wick and scheduling the filtered direction independently. The recovered feature and shared schedule reproduce the original 1,278 / 340 / 312 counts and W/L/D values exactly.

## Guardrails / next experiment

- Do not optimize the 0.1-pip threshold or add filters using this already inspected sample.
- Do not promote this to production HydraAI or live trading.
- The next meaningful test is prospective, on fresh non-OTC Pocket Option demo observations, with all qualifying and rejected signals logged, actual entry/settlement quotes, displayed payout, and timestamp/latency.
- Separately, test other deliberately weak rules using the same exact-complement protocol, but freeze each rule before evaluation and correct for the number of candidates/horizons screened.

Data: 486,488 EUR/USD M1 Dukascopy BID candles, 68 continuous segments, 2025-07-21 to 2026-11-05. SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`. BID candles are not Pocket Option executable quotes; actual platform payout and settlement are not represented.
