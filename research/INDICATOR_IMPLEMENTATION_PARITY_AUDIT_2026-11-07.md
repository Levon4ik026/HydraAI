# Indicator implementation parity audit — 2026-11-07

Branch: `hydra/research-validation`  
Scope: static source comparison plus deterministic synthetic tests. Research-only; no signal thresholds or production code changed.

## Findings

### ATR(14)

The current exploratory screen's `screen_put_strategies.atr()` and the frozen candidate's `frozen_put_candidate.wilder_atr()` are algorithmically identical:

1. True range at index 0 is high minus low.
2. Later true range is max(high-low, abs(high-previous close), abs(low-previous close)).
3. Initial ATR at index 13 is the arithmetic mean of the first 14 true ranges.
4. Later values use Wilder recursion: `(previous_atr * 13 + current_tr) / 14`.

The frozen candidate imports the same shared `Bar` type and `indicators()` implementation as the research screen for ADX, Bollinger and Williams %R. The duplicate ATR function is currently redundant but has matching behavior. A deterministic test compares both outputs to 15 decimal places over a synthetic 120-bar OHLC series.

**Important distinction:** algorithm parity does not establish the provenance of the fixed threshold `0.0003596314`. The screen script currently contains the ATR function but does not derive that floor. The feature-separation report describes ATR/close as a ranked diagnostic, not the source of this exact floor. Git history narrows the trace but does not resolve it: the exact literal first appears in the initial `Freeze PUT candidate for prospective validation` commit (`6fdba1f`, 2026-11-07). The parent commit does not contain this candidate file, and no earlier derivation or calculation is present in the inspected repository history. Therefore the value is traceable to the freeze commit, but its mathematical calibration provenance remains unverified. It stays frozen for the live prospective experiment.

### Bollinger Bands (20, 2)

The shared indicator function calculates a rolling 20-close mean and population standard deviation (variance divisor 20, equivalent to `ddof=0`). The upper band is mean + 2 standard deviations. This is now explicitly tested against an independent calculation and distinguished from sample standard deviation (`ddof=1`).

### Williams %R (14)

The shared function uses the rolling 14-bar highest high and lowest low and computes:
`-100 * (highest_high - current_close) / (highest_high - lowest_low)`.
If the range is zero, it returns -50. The rolling-window formula is covered by a deterministic independent test.

### ADX (14)

The shared implementation seeds smoothed TR and directional movement from the first 14 transitions (indices 1–14), calculates DX from index 14, seeds ADX with the arithmetic mean of the first 14 valid DX values (index 27), then applies Wilder recursion. The warm-up boundary is covered by a deterministic test.

The frozen candidate and the current screen both call this same shared implementation, so there is no separate ADX formula divergence between those two code paths. This does not prove equivalence with the missing original 2026-11-06 screening program.

## Signal and execution parity boundaries

- The frozen candidate applies a strict upper-band close re-entry and Williams %R cross below -20, ADX in [15,25), positive 3-bar close momentum, and the fixed ATR/close floor.
- The broad exploratory screen's `BB_WILLR:any/15/20` family does not include the momentum or ATR floor. It is therefore not a direct signal-set reproduction of the frozen candidate.
- Both code paths use complete UTC-aligned M5 bars and require the next M5 bar to be consecutive within a segment.
- The original 2026-11-06 executable selector and serialized train signal timestamps remain missing. The original 376-row holdout outcome log validates entry-candle settlement direction, not original signal-selection parity.

## Test coverage added

`research/tests/test_indicator_parity.py` verifies:
- screen ATR equals frozen candidate ATR;
- Bollinger upper band uses population standard deviation;
- Williams %R matches an independent rolling-high/low calculation;
- ADX remains unavailable until its 14-DX seed at index 27.

`research/tests/test_frozen_put_execution.py` additionally verifies that a signal is timestamped on the closed M5 candle, entry is the immediately following M5 open, settlement is that entry candle's close, changing the future entry candle changes only its outcome (not the prior signal or entry timestamp), and a nonconsecutive next candle is rejected.\n\nThese are deterministic implementation tests, not evidence of predictive edge.

## Decision

1. Correct the earlier blanket warning: current screen ATR and frozen-candidate ATR implementations match.
2. Keep the ATR floor frozen during prospective collection.
3. Do not claim the exact floor's calibration provenance until its original calculation is recovered.
4. Do not claim bit-for-bit reproduction of the missing original 2026-11-06 strategy.
5. Continue investigating original signal provenance and independent future validation; no production integration.
