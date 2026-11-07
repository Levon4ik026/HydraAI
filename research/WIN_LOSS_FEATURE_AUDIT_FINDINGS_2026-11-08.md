# CALL / PUT winner-vs-loser feature audit — 2026-11-08

## Reproduction

- Branch: `hydra/research-validation`
- Data: `eurusd_history_extended.csv`, 30,048 M1 rows; 6,008 complete UTC M5 bars; 2 continuous segments.
- Date range: 2026-10-07 through 2026-10-28 (source dataset).
- Frozen trigger: BB(20, 2) re-entry + Williams %R(14) cross; ADX(14) >= 15.
- Execution: signal at closed M5 candle, entry next M5 open, settlement at that candle close; 92% payout; no signal across gaps.
- Chronological boundary: 2026-10-21 19:05 UTC.
- Eligible signals: 145 total (CALL 86, PUT 59); draws retained but excluded from win/loss feature tests.

The full generated table (20 features, four direction/period cohorts) is available as GitHub Actions artifact **call-put-win-loss-feature-audit**, run 42418559727. This summary records the main interpretation.

## Outcome by direction and chronological period

| Side / period | W | L | D | Decisive WR | Net at 92% |
|---|---:|---:|---:|---:|---:|
| CALL train | 29 | 22 | 3 | 56.86% | +4.68 |
| CALL holdout | 23 | 9 | 0 | 71.88% | +12.16 |
| PUT train | 19 | 21 | 3 | 47.50% | -3.52 |
| PUT holdout | 8 | 8 | 0 | 50.00% | -0.64 |

Wilson 95% intervals for decisive WR:
- CALL train: 43.27–69.50%.
- CALL holdout: 54.63–84.44%.
- PUT train: 32.94–62.50%.
- PUT holdout: 28.00–72.00%.

These intervals are wide. Holdout groups are small, especially PUT (16 decisive trades).

## Feature separation: CALL

Twenty signal-time features were compared between wins and losses, independently within train and holdout. The strongest unadjusted train hints were:
- EMA20–EMA50 separation divided by ATR: winners median -0.716 vs losses -0.172; Cliff's delta -0.392; Mann–Whitney p=0.0179, BH q=0.1789.
- Upper-wick/range: winners 0.0746 vs losses 0.1615; delta -0.406; p=0.0142, q=0.1789.
- Body/range: winners 0.6458 vs losses 0.4858; delta +0.351; p=0.0340, q=0.2264.

None survives Benjamini–Hochberg correction across the 20 tested features.

Crucially, these train hints do not repeat in holdout:
- EMA separation: winners -0.589 vs losses -0.848; delta +0.063 (direction/size of effect collapses and changes sign).
- Upper-wick/range: winners 0.1389 vs losses 0.0455; delta +0.527 (reverses direction).
- ATR/close: train winners were higher than losses (0.000342 vs 0.000293), while holdout winners were lower (0.000172 vs 0.000333); holdout p=0.0189 but BH q=0.2359.

Interpretation: no stable CALL winner fingerprint was found. The apparently interesting training candle-shape/trend features either fail correction or reverse in holdout.

## Feature separation: PUT

No tested PUT feature survived multiple-testing correction in either period. No unadjusted feature was below p=0.05 in PUT train or PUT holdout.

Closest holdout hint:
- +DI minus -DI: winners median +14.66 vs losses +5.63; Cliff's delta +0.562; p=0.0661, BH q=0.7571. This is based on only 8 wins and 8 losses and is not confirmatory.

Train PUT showed no clear separation in RSI, ADX, DMI, volatility, Bollinger position/width, EMA separation, momentum or candle anatomy. The 16-deal holdout is too small to infer a stable pattern from its quartile fluctuations.

## Statistical method and limitations

- Continuous feature distributions compared with a tie-corrected normal-approximation Mann–Whitney U test.
- Effect magnitude summarized with Cliff's delta.
- BH false-discovery correction applied separately to each direction x period family (20 feature tests per family).
- Quartile win rates are descriptive only; quartile cut points are calculated within each displayed cohort and are not candidate rules.
- Draws are excluded from decisive winner-vs-loser comparisons.
- Naive p-values do not account for serial dependence or overlapping market regimes. This remains exploratory.
- Feature values are computed from the fully closed signal candle only; the settlement candle is used only to label outcome.

## Verdict

**No robust single-feature winner pattern has been identified for CALL or PUT.**

CALL has a positive result in both periods, but the train-side feature hints do not carry over to holdout. PUT is negative in train and nearly flat in the small holdout, with no meaningful univariate feature separation. The analysis does not justify a CALL-only system, a PUT filter, or a change to the Desktop math core.

## Next research step

Do not search thresholds in the holdout. The next defensible step is a preregistered, low-dimensional interaction study on train only (for example: volatility x candle anatomy, and trend separation x wick structure), with a strict cap on candidate interactions. Freeze any resulting hypothesis before a later untouched prospective dataset. Keep CALL and PUT independent and compare net result, coverage, drawdown and uncertainty at 92%.
