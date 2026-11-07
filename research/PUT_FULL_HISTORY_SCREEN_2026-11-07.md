# Full-history PUT-only screen — exploratory update (2026-11-07)

Branch: `hydra/stabilization`  
Payout: **92% only** (+0.92 / -1.00 / 0 draw).  
Scope: research-only. No Desktop, production math core, or automatic trading changes.

## Dataset and protocol

- Source: recovered `eurusd_research_clean.csv`, 486,488 M1 rows, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.
- Source SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- Aggregation: complete UTC-aligned M5 buckets only; 97,227 complete M5 bars across 68 continuous segments. Missing buckets split segments; no trade crosses a gap.
- Chronological split by M5 bar count: 70% train / 30% holdout; boundary 2026-06-17 05:00 UTC.
- Signal at M5 close; entry next M5 candle; outcome by entry candle close vs open. Non-overlapping trades per candidate; a new signal at the prior trade's expiry close is allowed.
- Decisive break-even at 92% payout: 52.0833%.

## Main finding

**None of the 18 PUT-only variants produced positive net in both train and holdout.** The two most interesting candidates failed in opposite directions:

| Candidate | Train decisive / WR / net | Holdout decisive / WR / net |
|---|---:|---:|
| RSI fade 65 | 58 / 55.17% / +3.44 | 18 / 27.78% / -8.40 |
| CCI fade 100 | 721 / 51.73% / -4.84 | 279 / 55.20% / +16.68 |
| BB upper re-entry + Williams, ADX≥15 (screen implementation) | 768 / 49.87% / -32.64 | 373 / 49.87% / -15.88 |
| Stochastic bearish cross | 1,018 / 48.82% / -63.76 | 417 / 51.08% / -8.04 |
| EMA20 pullback below EMA50 | 2,012 / 47.27% / -186.08 | 876 / 49.32% / -46.56 |
| Donchian breakdown, 40 | 2,505 / 47.15% / -237.48 | 1,045 / 47.94% / -83.08 |

Other variants (MACD histogram zero-cross, CCI/RSI alternatives, bearish engulfing, ATR expansion, and shorter Donchian windows) were also net-negative in at least one split; none qualified as a stable candidate.

### CCI fade: a regime-shift lead, not an edge

CCI(20) crossing down through +100 while price is below EMA50 produced:
- Train: 754 trades, 721 decisive, 373 wins / 348 losses, 51.73%, -4.84 units. Wilson 95% CI 48.09–55.36%.
- Holdout: 288 trades, 279 decisive, 154 wins / 125 losses, 55.20%, +16.68 units. Wilson 95% CI 49.33–60.92%; one-sided binomial p=0.163 against 52.0833%.
- Full: 1,042 trades, 1,000 decisive, 52.70%, +11.84 units. Wilson 95% CI 49.60–55.78%; one-sided p=0.360.

The holdout point estimate is promising only in isolation; the confidence interval includes losses and the train estimate is below break-even. Monthly outcomes are unstable: positive in Jul/Aug/Oct 2025, negative Nov 2025 and Feb/Apr 2026, then mixed thereafter. This is not evidence of a persistent edge and must not be promoted.

### Why the old BB/Williams PUT result is still unresolved

This full-history screen does not reproduce the old 376-trade PUT holdout log. A direct application of the currently committed strict upper-band/Williams crossing rule with the current ADX implementation produces a different signal set. The saved log's 376 outcomes were previously checked against their corresponding entry-candle OHLC direction, but that validates settlement mapping—not the original signal-selection logic.

The current screen's BB row is a separate implementation-level exploratory comparison, not a reproduction of the old broad result. Do not infer that the historical edge was disproved by this screen until the original signal code, indicator initialization, data version, and scheduler ordering are recovered.

## Research implementation caveats

This was an independent full-history calculation from the recovered CSV, using the same named candidate families and trade timing as the branch screen. The pandas-based exploratory implementation uses Wilder-style exponentially smoothed approximations for several indicators and a seeded EMA approximation; it is not yet a bit-for-bit execution of `screen_put_strategies.py`. The BB/Williams/ADX result in particular is not suitable for resolving the old-rule discrepancy. The CCI family is a useful diagnostic lead but also needs exact implementation parity and a fresh forward test.

The 18 candidates and many variants create multiple-comparison risk. The holdout has already been examined in previous research and is not a pristine final test. No p-value here should be treated as confirmatory.

## Decisions and next steps

1. Do not promote any candidate; keep CALL frozen and PUT discovery separate.
2. Recover the exact original broad-screen implementation and reconcile signal timestamps against the 376-trade log before interpreting its historical edge.
3. Re-run the full-history candidate screen with exact branch indicator seeding and a single audited scheduler; keep the 92% payout and gap rules fixed.
4. Any new hypothesis must be frozen on earlier data and tested once on later, untouched data. Report month-by-month results and confidence intervals.
5. Only after independent CALL and PUT evidence exists, test their joint behavior under one shared scheduler and WAIT/conflict handling.

No Desktop or production files were changed.
