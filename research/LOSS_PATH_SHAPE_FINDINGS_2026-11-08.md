# HYDRA — Full-history loss anatomy with causal OHLC path features

Date: 2026-11-08  
Branch: `hydra/research-validation`  
Workflow: `42480522763`  
Artifact: `hydra-causal-regime-20m-audit`

## Scope

Re-ran the frozen 20-minute BB(20,2) re-entry + Williams %R(14) cross + ADX(14)>=15 rule on the full Dukascopy EURUSD M1 BID history. Entry is next M5 open; settlement is the fourth M5 close. Payout accounting is +0.92u / -1u / 0u.

Added 12 signal-close OHLC path descriptors to the causal audit: 6/12-bar path efficiency, 6-bar direction flips, 3-bar range overlap, 3-vs-12 range compression, close location, position in prior 12-bar range, 3-bar direction agreement, median range / true range, same-color run, direction-aligned body and direction-aligned close location. These use only the signal candle and prior candles; settlement candles are outcome labels only.

Data and split are unchanged: 1,048,666 M1 rows; 207,332 complete M5 bars; 2,634 continuous segments; 3,986 raw events; 3,459 eligible after 50-bar warmup and full 20-minute path checks. Purged splits: TRAIN 2,005; VALIDATION 712; TEST 742.

## Main finding

The added OHLC path descriptors do not reveal a stable, large loss fingerprint. Most standardized loss-vs-win effects are small (absolute Cohen's d generally below 0.25) and change direction between chronological periods.

### Examples

- CALL `range_overlap_3`: loss-vs-win d = +0.001 TRAIN, +0.205 VALIDATION, +0.123 TEST. The direction repeats after TRAIN, but the TRAIN effect is effectively zero and the later effects are small.
- PUT `range_compression_3v12`: d = +0.050 TRAIN, +0.046 VALIDATION, +0.095 TEST. Same sign, but all effects are weak.
- CALL `efficiency_12`: d = -0.036 TRAIN, -0.042 VALIDATION, -0.155 TEST. Same sign, still weak and not a sufficiently discriminating feature.
- PUT `close_location`: d = +0.089 TRAIN, -0.255 VALIDATION, +0.118 TEST. The association reverses in VALIDATION.
- CALL `range_atr`: d = -0.038 TRAIN, +0.242 VALIDATION, +0.022 TEST. A relatively larger validation-only hint does not persist.

No feature justifies a standalone filter. The train-defined quartile tables are highly non-monotonic and show substantial period drift. For example, CALL `efficiency_12` has TRAIN Q1/Q4 decisive WR 47.8%/54.6% but TEST Q1/Q4 48.8%/60.0%; intermediate bins and validation do not establish a monotonic rule. PUT `efficiency_6` TEST Q4 is weak (41.0% WR) but this is not supported by a stable TRAIN/VALIDATION pattern.

## Interpretation

This is evidence against the simple idea that a single candle-shape or short-path statistic can reliably identify the losing signals. The current indicator and OHLC context features are not separating wins and losses strongly enough. The result does not prove that no nonlinear interaction exists, but any interaction search now carries substantial multiple-testing risk.

## Next controlled step

Do not tune thresholds on TEST. If proceeding, predeclare a very small set of interpretable interaction hypotheses using TRAIN only, compare them against matched non-signal background states, freeze them before validation, and require stability in VALIDATION before even inspecting TEST. Any candidate then requires genuinely fresh, prospective Pocket Option DEMO candles. Dukascopy BID is a proxy and cannot establish exact platform execution outcomes.

No strategy parameters, local Desktop files, or automatic trading behavior were changed.
