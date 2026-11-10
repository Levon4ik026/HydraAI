# HydraAI — literature map and testable market-situation hypotheses

**Date:** 2026-11-10  
**Purpose:** Generate research hypotheses for the candidate-discovery stage. Papers are not evidence that a setup works on EUR/USD M1/M5 or on Pocket Option quotes.

## Evidence map

| Work | Market / data | Finding relevant to HydraAI | Testable hypothesis | Important limitation |
|---|---|---|---|---|
| Osler (2001), *Currency Orders and Exchange-Rate Dynamics: Explaining the Success of Technical Analysis*, NY Fed Staff Report 125 | FX order placement and exchange-rate dynamics | Take-profit clustering may reinforce reversals near predictable levels; stop-loss clustering may reinforce moves after levels are crossed; orders cluster around round numbers. | Separate level rejection / sweep-and-reclaim from breakout continuation; test round-number reactions. | We do not observe actual dealer orders or stop placement in Dukascopy OHLC. Only price-based proxies are available. |
| Ben Omrane & Van Oppens (2004), *The Predictive Success and Profitability of Chart Patterns in the Euro/Dollar Foreign Exchange Market* | Intraday EUR/USD; 12 chart patterns | Some patterns were statistically predictable, but only a small subset was profitable after costs; detection method mattered. | Test objective OHLC/extrema-based patterns and compare them with close-only definitions. | Older sample and execution/cost assumptions differ from present M1/M5 binary-option evaluation. |
| Ben Omrane & Van Oppens (2006), *The Performance Analysis of Chart Patterns* | EUR/USD intraday 5-minute data | Pattern performance assessed with Monte Carlo methods. | Use M5 as a natural event-definition timeframe and compare pattern results against randomized / matched baselines. | Historical period and market microstructure differ; not a Pocket Option study. |
| Alanazi et al. (2020), *The Bullish and the Bearish Engulfing Patterns: Beating the Forex Market or Being Beaten?* | 24 FX pairs; daily and H4 evidence | Engulfing patterns examined across broad FX data. | Treat candle patterns as hypotheses; test on our own chronological M5 data rather than importing published conclusions. | D1/H4, not M1/M5. |
| Hassanniakalager, Sermpinis & Stasinakis (2021), *Trading the Foreign Exchange Market with Technical Analysis and Bayesian Statistics* | EUR/USD, GBP/USD, USD/JPY; 7,846 technical rules | Data-snooping-aware evaluation and Bayesian combinations can improve selected rules. | After candidate discovery, test predeclared combinations of independently defined signals using TRAIN only; validate once. | Combination search can amplify overfitting; no validation/test tuning. |
| Elaut, Frömmel & Lampaert (2018), *Intraday Momentum in FX Markets* | Intraday FX activity | Intraday momentum varies with liquidity demand and trading hours. | Report event performance by UTC session; test whether impulse continuation/reversal is session-dependent. | Study market and instruments differ; no true order-flow feed in our OHLC data. |
| Frömmel & Lampaert (2016), *Does Frequency Matter for Intraday Technical Trading?* | Tick-level RUB/USD and technical rules | Apparent high-frequency edges can be erased by realistic time-varying costs. | Keep entry timing and expiry explicit; treat BID data and fixed payout as a proxy, not executable Pocket Option outcomes. | RUB/USD and managed-rate context; cost structure differs. |
| Caporale & Plastun (2020), *Daily Abnormal Price Changes and Trading Strategies in the FOREX* | Multiple FX pairs, daily abnormal moves | Abnormal moves can be followed by intraday continuation and later reversal effects. | Test continuation and exhaustion/reversal after objectively defined normalized impulses. | Daily/event-horizon findings do not establish M5 predictability. |
| Breedon & Ranaldo (2013), *Intraday Patterns in FX Returns and Order Flow* | High-frequency FX returns and order flow | Intraday return patterns relate to trading hours and local order flow. | Stratify results by UTC session and avoid pooling structurally different hours without checking. | We lack order-flow observations; session is only a proxy. |

## Primary source links

1. Osler (2001), New York Fed: https://www.newyorkfed.org/research/staff_reports/sr125.html
2. Ben Omrane & Van Oppens (2004), UCLouvain repository: https://research.dial.uclouvain.be/entities/publication/c11c5875-6d1b-4908-8ec5-0934ec49daa2
3. Ben Omrane & Van Oppens (2006), UCLouvain repository: https://research.dial.uclouvain.be/entities/publication/64ebd7b1-4f85-4f38-ac0d-553c018d915b
4. Alanazi et al. (2020): https://www.tandfonline.com/doi/full/10.1080/1351847X.2020.1748679
5. Hassanniakalager et al. (2021), University of Bath: https://researchportal.bath.ac.uk/en/publications/trading-the-foreign-exchange-market-with-technical-analysis-and-b/
6. Elaut et al. (2018), DOI: https://doi.org/10.1016/j.finmar.2016.09.002
7. Frömmel & Lampaert (2016), DOI: https://doi.org/10.1016/j.frl.2016.04.014
8. Caporale & Plastun (2020), Brunel repository: https://dspace.brunel.ac.uk/handle/2438/20567
9. Breedon & Ranaldo (2013), DOI: https://doi.org/10.1111/jmcb.12032

## Sixth-wave discovery plan

The sixth wave is a **candidate screen**, not a validation exercise. It tests predeclared, observable price-action proxies:

1. Previous observed UTC-day high/low sweep and reclaim.
2. Previous observed UTC-week high/low sweep and reclaim.
3. Previous observed UTC-day high/low breakout close (continuation hypothesis).
4. Round-number rejection at 0.0025 and 0.0050 EUR/USD grids.
5. Three-bar normalized impulse continuation.
6. Three-bar normalized impulse exhaustion/reversal.

For every event family, ORIGINAL and INVERTED must use identical event timestamps, next-M5-open entry, expiry, and non-overlap schedule; only CALL/PUT is reversed. Expiries are 5/10/15/20/30/60 minutes. Report train/validation/test chronologically, purge split-crossing outcomes, and do not use TEST to select candidates. Session breakdown is descriptive only and is not a license to tune session filters.

## Fixed research constraints

- Source: Dukascopy EUR/USD M1 BID aggregated to complete M5 bars. No OTC.
- Entry: next M5 open; expiry: close of the Nth subsequent M5 candle.
- Assumed payout: 92% only; WIN +0.92u, LOSS -1u, DRAW 0u. Break-even decisive WR = 52.0833%.
- No actual order book, stop orders, broker quotes, Pocket Option payout history, spread, or latency are observed/modelled.
- Use only features available at signal close. Levels must come from already completed periods.
- One active trade per family/expiry/continuous data segment; same schedule for original and inverse.
- A discovery screen cannot promote a candidate. Prior TEST periods are not pristine after repeated exploration.
- Report sample size, uncertainty, drawdown, streaks, multiple-testing exposure, and source limitations. Wilson intervals do not correct serial dependence.
- The target for a promising candidate remains VALIDATION >=57% decisive WR with meaningful sample and positive assumed-payout net; 56.0–56.9% is borderline. This is a discovery threshold, not proof.
