# HydraAI — literature-derived strategy register

**Branch:** hydra/research-validation  
**Status:** research intake; no candidate is promoted.  
**Scope:** EUR/USD first; M1/M5 preferred; manual CALL/PUT/WAIT research only. OTC and automated execution are excluded.

This register separates what a source actually specifies/reports, our operational interpretation, and what still needs verification. A published win rate is not assumed to transfer to HydraAI data, expiry, quotes, or payout.

## Intake rules

1. Prefer peer-reviewed papers with full text and exact entry/exit definitions.
2. Preserve original timeframe, data source, indicator units, direction, and expiry. Any change is a separately labelled adaptation.
3. Never fill gaps in a paper's specification silently. Mark the rule BLOCKED_SPEC until resolved.
4. Reproduce the original rule first; only then test variants. Inversion is a separate paired experiment on the exact same event timestamps.
5. Our own tests follow the research charter: chronological TRAIN / VALIDATION / TEST, purge split-crossing outcomes, 92% payout scenario unless actual payout is available, non-overlap schedule, uncertainty and multiple-testing caveats.
6. Report binary-option decisive WR separately from return-based or directional accuracy metrics in papers. At 92% payout, decisive break-even WR is 52.083%; draws are excluded from decisive WR and score 0u.
7. Historical Dukascopy BID outcomes are only a proxy for Pocket Option executable quotes.

## Candidate register

| ID | Candidate / source | Source market and timeframe | Source result | HydraAI status |
|---|---|---|---|---|
| LIT-001 | Price/EMA crossover, four EMA lengths — Kolková (2017) | EUR/USD, M5, MT4 broker data, 65,000 rate observations, 2015-06-03 to 2016-04-19; digital/binary option | Paper reports profitable-signal ratios 77.21% (EMA 9), 77.68% (EMA 10), 78.28% (EMA 12), 79.01% (EMA 26), using a stated 85.01% payout | **BLOCKED_SPEC** — exact expiry and EMA period units are ambiguous; no downloadable trade ledger/data. High-priority forensic reproduction, not a validated edge. |
| LIT-002 | Technical-rule pool + Bayesian forecasting — Hassanniakalager, Sermpinis & Stasinakis (2021) | EUR/USD, GBP/USD, USD/JPY; daily data. Four rolling 3-year IS / 1-year OOS exercises. | Peer-reviewed paper reports small technical-rule margins; Bayesian model portfolios improve risk-adjusted/return performance. EUR/USD BNN(10): 5.8% average annualized return, Sharpe 0.53 across 2013–2016, after costs. Not a binary-option WR. | **RULE UNIVERSE VERIFIED; TOP RULE IDS NOT PUBLISHED IN REPO** — authors' MATLAB code and EURUSD.csv are public. Rule families/parameter grids extracted. Individual rule-level OOS leaderboard still needs source output or independent reproduction. |

## LIT-001 — Kolková (2017): exact source extraction

**Publication:** Andrea Kolková, “Testing EMA Indicator for the Currency Pair EUR / USD”, *International Journal of Entrepreneurial Knowledge*, 5(1), 2017, pp. 35–40. DOI: 10.1515/ijek-2017-0003 (the journal page also lists DOI 10.37335/ijek.v5i1.51).

**Primary sources**
- Full text PDF: https://ijek.org/index.php/IJEK/article/download/51/46
- Article page: https://ijek.org/index.php/IJEK/article/view/51

**What the paper says**
- EUR/USD M5, 65,000 rate observations, 2015-06-03 through 2016-04-19; MT4 broker-supplied data.
- The system is described as the current exchange rate crossing an EMA. Crossing upward is SELL; the opposite crossing is BUY.
- Four EMA lengths are reported: 9, 10, 12, and 26.
- Binary/digital options are used. The paper says “triple expiration” but does not clearly specify the actual expiry duration in the accessible methods text.
- The paper uses an 85.01% return rate/payout assumption.
- Reported profitable-signal ratios: EMA9 77.21% (10,771 / 13,951); EMA10 77.68% (10,272 / 13,223); EMA12 78.28% (9,456 / 12,079); EMA26 79.01% (6,418 / 8,123).
- Monthly results show a dramatic September collapse: approximately 42.5–43.3% for the four EMA settings, versus roughly 75–81% in many other months. This is a warning that performance may be regime/month dependent.

**Critical specification gaps**
1. The paper alternates between “9-day/10-day/12-day/26-day EMA” and M5 data. It does not clearly establish whether N means calendar days or M5 bars. Do not silently convert.
2. “Triple expiration” is not a sufficiently precise expiry specification for our simulator.
3. The paper does not provide a trade-by-trade ledger or downloadable underlying dataset.
4. The reported 77–79% must not be treated as an independently confirmed win rate: the signal/expiry mapping and exact scoring convention need clarification.
5. The source uses broker quotes and 85.01% payout, unlike our Dukascopy BID proxy and current 92% scenario.

**Reproduction protocol**
- Stage 0 (forensic): inspect all paper pages/tables and seek author clarification on EMA units and triple expiry. No backtest implementation may claim exact replication until these are resolved.
- Stage 1 (explicitly labelled proxy): if unresolved, test two separate hypotheses, not one:
  - LIT-001A_EMA_N_BARS: EMA N on completed M5 closes, N in {9,10,12,26}; CALL when close crosses from below to above EMA; PUT when close crosses from above to below. This is the opposite direction to the paper's written direction and must not be confused with it.
  - LIT-001B_EMA_N_BARS_INVERTED: exact inverse of A on identical timestamps.
  - A third paper-direction run may be added only as LIT-001C_PAPER_DIRECTION_PROXY: upward cross = PUT, downward cross = CALL.
- Use next M5 open for entry and test explicitly enumerated expiries (not “triple expiry” guessed). These are HydraAI operational conventions, not source-faithful replication.
- Preserve separate candidate IDs for each N and direction. Do not optimize N on TEST.
- Because the paper's September breakdown is reported, investigate month/session/volatility context only as a pre-registered secondary analysis; do not use it to retrofit a filter on TEST.

## LIT-002 — Hassanniakalager et al. (2021): replication source

**Publication:** Arman Hassanniakalager, Georgios Sermpinis & Charalampos Stasinakis, “Trading the Foreign Exchange Market with Technical Analysis and Bayesian Statistics”, *Journal of Empirical Finance* 63 (2021), pp. 230–251. DOI: 10.1016/j.jempfin.2021.07.006.

**Primary sources**
- Accepted manuscript: https://eprints.gla.ac.uk/246954/
- Authors' replication code: https://github.com/hkalager/FX_MHT_DMA

**Verified facts**
- The authors' rule-generator explicitly checks that the input file is available for a **daily period**; EURUSD.csv contains daily date rows (first observation: 2007-09-18). This is not an M1/M5 source strategy set.
- Step1_MainRunner uses four rolling exercises: 2010–2012 IS → 2013 OOS; 2011–2013 → 2014; 2012–2014 → 2015; 2013–2015 → 2016. The IS pool is first filtered to its top 5% by cumulative return, then subjected to Romano–Wolf k-FWE data-snooping control. Survivors are ranked by accuracy and the top 5/10/15 feed the Bayesian models. OOS transaction cost is 3 basis points per trade. The code fixes DMA alpha=0.90 and lambda=0.99.
- The exact rule families in rulegenerator.m are Filter, MA Cross, Support & Resistance, Channel Breakout (CHB), and OBV. No EMA+RSI or Bollinger+RSI combined strategy is provided by this code.
- MA Cross uses simple moving averages, not EMAs, with periods {2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 125, 150, 200, 250}; all fast/slow pairs with fast < slow are generated, plus additional threshold/delay/holding variants.
- Filter rules start with price-move thresholds {0.5%, 1%, 1.5%, 2%, 2.5%, 3%, 3.5%, 4%, 4.5%, 5%, 6%, 7%, 8%, 9%, 10%, 12%, 14%, 16%, 18%, 20%, 25%, 30%, 40%, 50%}; further variants add lookback/holding constraints.
- Support/resistance uses rolling high/low extremes with lookbacks {5, 10, 15, 20, 25, 50, 100, 150, 200, 250}, or rolling close extremes {2, 3, 4, 5, 10, 20, 25, 50, 100, 200}; variants include fixed holding periods {0, 5, 10, 25, 50}.
- Channel Breakout uses lookbacks {5, 10, 15, 20, 25, 50, 100, 150, 200, 250}, channel thresholds {0.5%, 1%, 2%, 3%, 5%, 7.5%, 10%, 15%}, additional bands {0.1%, 0.5%, 1%, 1.5%, 2%, 3%, 4%, 5%}, and holding periods {5, 10, 25, 50}.
- OBV uses moving-average crossovers across the same 15 periods, with variants for bands, delay, and holding period. The code includes a small parameter-label typo in the OBV case 2/3/4 strings (references bsercross/dsercross/csercross instead of the OBV arrays); reproduce calculations from the actual arrays, not labels blindly.
- Important: these are position-state/trend rules that can hold until reversal or a programmed holding interval. They are not fixed-expiry CALL/PUT signals. Converting them to binary-option entries/expiry is a new adaptation and must be reported separately.
- It applies a data-snooping procedure (Romano et al. test with Romano–Wolf balancing; k=39, about 0.5% of 7,846 rules) to identify promising rules. The paper reports three basis points transaction costs per trade.
- Selected rules are combined with Naïve Bayes, Relevance Vector Machine, Dynamic Model Averaging, Dynamic Model Selection and Bayesian regularized neural network.
- The abstract reports small margins from technical analysis and says Bayesian methods can increase profitability substantially. In the EUR/USD appendix table selected by in-sample excess return, BNN with 10 top rules reports 5.8% average annualized return and 0.53 Sharpe across 2013–2016; BNN with 15 rules reports 5.5% and 0.53. These are model-portfolio return/Sharpe metrics after costs, not WR or binary-option outcomes.
- The public author repository includes EURUSD.csv, rulegenerator.m, Step1_MainRunner.m, model code and README. The README describes OHLCV data from an anonymous FX brokerage and warns results may not reproduce exactly because random seeds are used.

**What is and is not recoverable**
- The published paper reports aggregate Bayesian model portfolios, not a standalone binary-options win rate for a named rule.
- The public repository contains source code and price data but does not include the generated EUR/USD in-sample/OOS MAT files or an exported top-rule ledger. The exact top rule IDs and their per-rule OOS metrics therefore cannot be honestly extracted from the repository snapshot alone.
- The authors' scripts use MATLAB functions/toolboxes and stochastic bootstrap/model components. A faithful reproduction requires rebuilding their pipeline or obtaining their generated result files; it is not a quick direct port into HydraAI.

**Next forensic tasks**
1. Obtain or independently recreate the authors' generated EUR/USD top-rule list, including rule index, category, parameters, IS return, OOS year and OOS result.
2. Prioritize interpretable candidates (SMA Cross, Filter, CHB, S&R) with stable multi-year OOS evidence; don't select solely by the best in-sample return.
3. If adapting any of these to M1/M5 binary expiries, register it as a new HydraAI adaptation, not source-faithful replication.

## Deferred hypotheses (not yet literature-verified)

The following are research ideas only; do not label them as published combinations until a specific primary source with exact rules is attached:
- Bollinger mean-reversion / re-entry
- Bollinger + RSI confirmation
- RSI(2) mean reversion
- MACD + RSI
- Donchian breakout
- Mean reversion + momentum
- Piercing Line / Dark Cloud Cover

Each needs its own primary citation, full rule definition, timeframe, data period, reported metric, and specification-quality rating before implementation.

## Change log

- 2026-11-10: created literature intake register; added LIT-001 and LIT-002 with source-level details and unresolved-specification flags. Deep-inspected LIT-002 Step1_MainRunner.m, rulegenerator.m, filter_inputs.m, DS_Test.m and EURUSD.csv. Recorded daily frequency, rolling splits, filter + k-FWE selection, exact rule families/parameter grids, OOS costs, and the missing per-rule leaderboard. No candidate promoted and no TEST-driven tuning performed.
