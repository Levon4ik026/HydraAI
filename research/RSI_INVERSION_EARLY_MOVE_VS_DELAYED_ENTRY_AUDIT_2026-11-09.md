# RSI Inversion — Early-Move Predictability vs Delayed Entry Audit (2026-11-09)

## Executive conclusion

The first 1–5 minutes after an inverted RSI(14) signal contain information about the eventual 15-minute close, but the strongest-looking relationship is largely not actionable by simply waiting for confirmation.

Key result:
- Among the baseline 15-minute cohort, if the first five minutes move strongly in the signal direction (top TRAIN-defined tercile, signed return > +1.0 pip), the original 15-minute expiry win rate is about 78–80% in all three splits.
- If the first five minutes move strongly against the signal (bottom tercile, signed return <= -0.7 pip), the original 15-minute expiry win rate is only 23–27%.
- But by the time those five minutes have elapsed, much of the movement has already occurred. Entering after minute five and holding only until the original 15-minute expiry does **not** preserve the apparent advantage: the high-confirmation rule produces only 49.16% TEST decisive WR and -33.28u at a hypothetical 92% payout.
- Reversing direction after a strongly adverse first five minutes is also unprofitable: 49.17% TEST decisive WR, -30.20u.

This is a useful negative result: do not confuse a post-entry path descriptor with a tradable early-entry signal.

## Dataset and exact method

- Dataset: `eurusd_research_clean.csv`, 486,488 EUR/USD M1 BID bars.
- Coverage: 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC; 68 continuity segments.
- SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- RSI(14): Wilder smoothing, SMA seed over the first 14 changes within each continuity segment, recursive smoothing thereafter.
- Original deliberately adverse rule: RSI crosses above 70 -> CALL; crosses below 30 -> PUT.
- Inverted direction: cross above 70 -> PUT; cross below 30 -> CALL.
- Signal is known at signal candle close. Baseline entry is next M1 candle open.
- Baseline expiry: close of the 15th entry candle (15 minutes after baseline entry).
- One-position schedule: next signal is eligible only when its signal candle index is at or after the previous trade's expiry candle index. Each candidate strategy has its own schedule; if a filter rejects a signal, no position is opened and it does not block later signals.
- TRAIN: before 2026-05-08. VALIDATION: 2026-05-08 through 2026-08-05. TEST: from 2026-08-06. Trades crossing a split boundary or data gap are removed.
- Hypothetical fixed payout: +0.92u win, -1u loss, 0u draw. Break-even decisive WR = 52.0833%.
- All outcomes use directional close-vs-entry-open; draws excluded from decisive WR.

### Reproducibility note

This independent implementation generates 5,199 TRAIN, 1,473 VALIDATION and 1,510 TEST baseline scheduled events. Prior reports list 5,197 / 1,473 / 1,508. The small remaining discrepancy (2 TRAIN and 2 TEST events) is not silently reconciled. It likely reflects a minor RSI initialization/scheduling boundary difference in the earlier screen. This audit uses one internally consistent implementation throughout. The original report generator should be located and unified before treating the historical screens as exact replications.

## 1. Baseline result in this implementation

| Split | Trades | W | L | D | Decisive WR | Net units |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 5,199 | 2,753 | 2,374 | 72 | 53.70% | +158.76 |
| VALIDATION | 1,473 | 764 | 685 | 24 | 52.73% | +17.88 |
| TEST | 1,510 | 803 | 673 | 34 | 54.40% | +65.76 |

## 2. First-five-minute movement is strongly associated with the original 15-minute outcome

Define signed 5-minute movement in pips from baseline entry open to the close of the fifth entry candle, positive when it moves in the inverted signal direction.

Tercile boundaries were calculated from TRAIN only:
- LOW: signed movement <= -0.7 pip.
- MID: > -0.7 and <= +1.0 pip.
- HIGH: > +1.0 pip.

### Original 15-minute outcome, grouped by the first five minutes

| Split | First-5m bucket | Trades | W | L | D | Decisive WR | Net units |
|---|---|---:|---:|---:|---:|---:|---:|
| TRAIN | LOW | 1,745 | 457 | 1,274 | 14 | 26.40% | -853.56 |
| TRAIN | MID | 1,746 | 969 | 729 | 48 | 57.07% | +162.48 |
| TRAIN | HIGH | 1,708 | 1,327 | 371 | 10 | 78.15% | +849.84 |
| VALIDATION | LOW | 467 | 107 | 354 | 6 | 23.21% | -255.56 |
| VALIDATION | MID | 574 | 323 | 239 | 12 | 57.47% | +58.16 |
| VALIDATION | HIGH | 432 | 334 | 92 | 6 | 78.40% | +215.28 |
| TEST | LOW | 466 | 122 | 336 | 8 | 26.64% | -223.76 |
| TEST | MID | 631 | 353 | 255 | 23 | 58.06% | +69.76 |
| TEST | HIGH | 413 | 328 | 82 | 3 | 80.00% | +219.76 |

This is a strong descriptive relationship and it repeats across the chronological splits. But it is measured after the first five minutes of the original trade have already elapsed. It is not a valid result for entering at the original entry price.

## 3. Can we wait five minutes and enter later?

To make the idea causal:
- Observe the first five complete entry candles.
- At the fifth candle close, evaluate the condition.
- If accepted, enter at the next candle open.
- Exit at the original 15-minute expiry close. This leaves approximately 10 minutes in the market.
- Thresholds are frozen from TRAIN: confirmation means signed first-five-minute movement > +1.0 pip; low-adverse means maximum adverse excursion <= 0.633 pip.

Each rule is rescheduled independently, and rejected signals do not block later signals.

### Delayed-entry strategy results

| Rule | Split | Trades | W | L | D | Decisive WR | Net units |
|---|---|---:|---:|---:|---:|---:|---:|
| Wait 1m, enter regardless | TRAIN | 5,199 | 2,718 | 2,396 | 85 | 53.15% | +104.56 |
| Wait 1m, enter regardless | VALIDATION | 1,473 | 772 | 680 | 21 | 53.17% | +30.24 |
| Wait 1m, enter regardless | TEST | 1,510 | 794 | 683 | 33 | 53.76% | +47.48 |
| Wait 3m, enter regardless | TRAIN | 5,199 | 2,654 | 2,436 | 109 | 52.14% | +5.68 |
| Wait 3m, enter regardless | VALIDATION | 1,473 | 768 | 679 | 26 | 53.08% | +27.56 |
| Wait 3m, enter regardless | TEST | 1,510 | 791 | 688 | 31 | 53.48% | +39.72 |
| Wait 5m, enter regardless | TRAIN | 5,199 | 2,684 | 2,421 | 94 | 52.58% | +48.28 |
| Wait 5m, enter regardless | VALIDATION | 1,473 | 758 | 685 | 30 | 52.53% | +12.36 |
| Wait 5m, enter regardless | TEST | 1,510 | 781 | 699 | 30 | 52.77% | +19.52 |
| Wait 5m, only if signed move > +1.0 pip | TRAIN | 2,437 | 1,224 | 1,173 | 40 | 51.06% | -46.92 |
| Wait 5m, only if signed move > +1.0 pip | VALIDATION | 621 | 308 | 302 | 11 | 50.49% | -18.64 |
| Wait 5m, only if signed move > +1.0 pip | TEST | 606 | 291 | 301 | 14 | 49.16% | -33.28 |
| Wait 5m, only if adverse excursion <= 0.633 pip | TRAIN | 2,365 | 1,183 | 1,128 | 54 | 51.19% | -39.64 |
| Wait 5m, only if adverse excursion <= 0.633 pip | VALIDATION | 695 | 354 | 320 | 21 | 52.52% | +5.68 |
| Wait 5m, only if adverse excursion <= 0.633 pip | TEST | 704 | 356 | 329 | 19 | 51.97% | -1.48 |

The delayed confirmation rule fails in all three splits at the 92% payout hurdle. Waiting without a filter also reduces the aggregate edge compared with immediate entry.

## 4. Can we reverse after the first five minutes go against us?

A separate causal test was run:
- Wait for the first five candles.
- If signed movement is <= -0.7 pip against the original inverted signal, enter in the opposite direction at the next open.
- Exit at the original 15-minute expiry close.
- Independently schedule these reverse trades.

| Split | Trades | W | L | D | Decisive WR | Net units |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 2,027 | 924 | 1,074 | 29 | 46.25% | -223.92 |
| VALIDATION | 546 | 250 | 288 | 8 | 46.47% | -58.00 |
| TEST | 544 | 265 | 274 | 5 | 49.17% | -30.20 |

This reverse-after-adverse-move idea also fails. The fact that the original 15-minute outcome is often a loss after an adverse first five minutes does not mean a late reverse entry has positive expectancy; much of the adverse move has already happened.

## 5. Interpretation

1. The first five minutes are highly informative about the eventual original 15-minute close.
2. This is partly a path/label relationship: the first five minutes are already included inside the 15-minute outcome window.
3. Waiting to enter after observing that move changes the entry price and leaves less time to expiry. The apparent 78–80% conditional win rate collapses to 49.16% for the delayed high-confirmation rule.
4. Reversing after a bad first five-minute move is also negative across all splits.
5. Therefore, the early-move filter is not a usable confirmation rule in this form. It should not be added to HydraAI.
6. A better next hypothesis would use information available before the original entry: pre-signal volatility, RSI crossing speed, candle range/body/wick, trend context, and distance to recent levels. Those can be calculated causally without consuming the option's expiry window.

## Decision

**No new deployable strategy found.** The early-move study explains why the path audit's conditional 80% result was misleading when interpreted as a potential filter. Immediate inverted RSI remains only a research candidate, and its regime stability is still unproven.

## Next research gate

Unify the original and independent RSI event generators so they produce exactly matching signal timestamps and schedule decisions. Then study pre-entry features only, with thresholds learned on TRAIN and frozen for VALIDATION/TEST. No production code changes or automated trading.