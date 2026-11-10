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



| LIT-003 | High-volatility EUR/USD intraday mean-reversion / paired long-short take-profit — Wiśniewska (2016; issue 2015) | EUR/USD M1 bid+ask, Bank of America, calendar year 2005, 252 trading days | Reports 95% of daily maximum-return observations positive for each leg under the paper's construction; paired strategy table reports positive outcomes in selected scenarios. Not a fixed-expiry signal or a 95% binary-option WR. | **SOURCE RULE EXTRACTED; BINARY ADAPTATION BLOCKED** — original is a daily-start paired position with intraday take-profit, no reusable event-by-event signal ledger; paper itself flags one-year sample and robustness questions. |
| LIT-004 | Regime-conditioned Z-score mean reversion with higher-timeframe momentum filter — Bhatti (2026, SSRN preprint) | Intraday FX framework; exact pair/timeframe/sample need full-text verification | Abstract describes volatility-normalized Z-score entries, higher-timeframe momentum regime filter and ATR/volatility-normalized sizing; explicitly methodological, not a guaranteed-profit claim. No verified performance metric. | **PREPRINT / SPECIFICATION AUDIT REQUIRED** — no performance evidence accepted yet; inspect formula, code, data and out-of-sample design before implementing. |
| LIT-005 | Prior-session extremes + VWAP deviation + ADX rollover — Bhatti (2026, SSRN preprint) | FX intraday; exact pair/timeframe/sample require verification | Abstract describes short near prior-session high / positive VWAP deviation with turning-over ADX; long symmetrically near prior-session low / negative VWAP deviation. The abstract explicitly says formal backtesting and performance attribution are future work. | **IDEA ONLY; NO BACKTEST EVIDENCE** — candidate can be reconstructed as a hypothesis only after full-text parameter and data audit; do not describe as proven strategy. |
| LIT-006 | Large-scale intraday technical-rule universe — Frömmel & Lampaert (2016) | RUB/USD tick transactions, 2000–2011; resampled 10/15/30/60-minute bars; >8,000 rules | Authors report technical profits appear more at higher frequency, but realistic observed, time-varying transaction costs erase most profitability; some exception during managed exchange-rate policy. Not EUR/USD and not binary options. | **NEGATIVE CONTROL / METHODOLOGY** — useful warning about costs and frequency; not a direct HydraAI candidate. |
| LIT-007 | Intraday FX technical rules selected by genetic programming and optimized linear forecasting — Neely & Weller (2003) | Intraday FX data; paper studies rules selected in-sample then evaluated out-of-sample | No excess returns after realistic transaction costs and trading hours, although some patterns were stable. | **NEGATIVE CONTROL / RESEARCH METHOD** — exact candidate rules are not yet extracted; use as guardrail against overfitting, not as a high-WR candidate. |



| LIT-008 | Eight-indicator intraday FX ensemble + genetic programming / reinforcement learning — Dempster et al. (2001) | GBP/USD, 15-minute bars from tick data; 1994–1998; rolling 1-year train / 1-month OOS, 48 OOS months | Authors report positive average annual OOS return at 1 bp slippage (GA 21.6%, RL 16.3%), but at 4 bp all methods are around zero/negative and at 8–10 bp results are small/unstable. Not a binary WR. | **HIGH-VALUE METHOD / NOT READY-MADE BINARY RULE** — exact indicator families and Boolean-combination method extracted; market is GBP/USD, not EUR/USD; strategy is stateful currency switching, not fixed expiry. |
| LIT-009 | M1 moving-average deviation / mean reversion diagnostics — Wiśniewska (2014/2015) | EUR/USD M1 LastBid, 2004–2006; moving-average windows from 60 to 7,200 minutes and 1–5 days; 24 entry hours assessed | ADF with drift rejects unit root (p≈0.009); deviations around moving averages show heavy tails. Study compares best attainable long/short returns within 24h, not forward fixed-horizon direction. | **MARKET PROPERTY / NOT AN ENTRY SYSTEM** — exact windows and analysis recovered; reported maximum favorable excursions are hindsight extrema and cannot be used as prospective win rate. |

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

- 2026-11-10: created literature intake register; added LIT-001 and LIT-002 with source-level details and unresolved-specification flags. Deep-inspected LIT-002 author code and daily EURUSD.csv. Recorded daily frequency, rolling splits, Romano–Wolf selection, exact rule families/parameter grids, OOS costs, and missing per-rule leaderboard. No candidate promoted and no TEST-driven tuning performed.
- 2026-11-10: added LIT-003 after full-PDF extraction of Wiśniewska's EUR/USD M1 volatility study; clarified that its 95% statement is about daily maximum returns and its strategy is paired spot long/short with take-profit, not fixed-expiry direction. Added two 2026 SSRN preprint hypotheses (LIT-004/005) without performance claims, plus intraday negative controls (LIT-006/007).
- 2026-11-11: full-PDF extracted LIT-009 (Wiśniewska 2014 EUR/USD M1 moving-average deviations) and LIT-008 (Dempster et al. 2001 eight-indicator ensemble/GA/RL). Recorded exact M1 MA windows, the hindsight maximum-excursion limitation, GBP/USD 15-minute source, rolling OOS design and slippage sensitivity. No reported metric was relabelled as binary WR; no candidate promoted.


## LIT-003 — Wiśniewska (2016): EUR/USD M1 volatility and mean reversion

**Publication:** Marta Anastazja Wiśniewska, “EUR/USD Intraday Volatility vs Trading Results and Market Efficiency”, *Argumenta Oeconomica Cracoviensia*, No. 13 (2015), pp. 33–42; journal record published 2016-02-01. DOI: 10.15678/AOC.2015.1302.

**Primary source:** https://ceeer.uek.krakow.pl/index.php/aoc/article/download/881/693/1521

**What the paper actually tests**
- One-minute EUR/USD bid and ask quotes from Bank of America, year 2005, 252 trading days. Each minute's last quoted transaction rate is used.
- It examines two conventional spot legs: short (sell at bid, later buy back at ask) and long (buy at ask, later sell at bid).
- The start time is either minute 1 of the day or minute 360 (06:00); for each start it examines all later minutes up to minute 1,440 as possible exit observations.
- The paper's later “high volatility + mean reversion” implementation opens both long and short positions simultaneously at minute 360 and uses separate take-profit targets: 0.00086 for the short leg and 0.0005 for the long leg.
- On days when targets are not reached (reported as 5% of sample), the paper evaluates six alternative mark/return conventions, including average return, average ± standard deviation, zero, minimum and maximum. This sensitivity is important: the result depends on how unresolved positions are scored.
- Reported annualized return for the combined strategy under the average-return convention is 7.9131% before any stated leverage; the paper discusses 1:25 leverage separately. It is not a win rate.
- The abstract's “95% probability” refers to the paper's distribution of daily maximum returns / target reachability construction, not to 95% profitable independent trades or 95% binary-option accuracy.

**HydraAI assessment**
- This is the most directly relevant new source so far because it uses EUR/USD M1 and both bid/ask sides.
- It is not a ready-made CALL/PUT signal: it opens paired opposing spot positions at a fixed time and closes on price targets, whereas HydraAI needs directional fixed-expiry outcomes. A binary-option conversion would be a new hypothesis.
- The source sample is only one calendar year (2005), the paper itself identifies robustness across start time and sample period as open questions, and its unresolved-position scoring scenarios need careful replication.
- Register as LIT-003 source reproduction / forensic study, not as a high-WR candidate. If adapted, freeze explicit M1 rules, entry, expiry and direction before TRAIN/VALIDATION evaluation; include both directions and paired inversion only on identical timestamps. Do not carry over the paper's 95% phrase as WR.

## LIT-004 — Bhatti (2026): regime-conditioned Z-score mean reversion (preprint)

**Source:** https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6087107

The accessible SSRN abstract describes volatility-normalized price deviations (Z-scores) as signal inputs, a higher-timeframe momentum state to avoid persistent trends, and volatility-adjusted sizing. It provides an implementation-oriented MT5/MQL5 prototype. The abstract calls this a methodological contribution and does not claim guaranteed profitability. The page lists no references and no citations. Full-text equations, market/pair, sample, costs, and any test results remain to be verified. Treat as an unvalidated hypothesis, not an evidence-backed performance candidate.

## LIT-005 — Bhatti (2026): ADX-conditioned VWAP reversion (preprint)

**Source:** https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6454659

The accessible abstract describes a mean-reversion setup combining prior-session highs/lows, VWAP deviation, and a turning-over ADX. It explicitly states that formal backtesting and performance attribution are left for future work. This is therefore an idea with a plausible rule outline, not a demonstrated profitable strategy. Before any HydraAI implementation, verify the complete formulas, session/VWAP construction, thresholds, instrument, and timing from the full text. Do not assign it a win rate.

## LIT-006 / LIT-007 — intraday technical-analysis cautionary controls

- Frömmel & Lampaert (2016), “Does frequency matter for intraday technical trading?”, *Finance Research Letters* 18, 177–183, DOI 10.1016/j.frl.2016.04.014. More than 8,000 rules on RUB/USD tick transactions (2000–2011), resampled to 10/15/30/60 minutes. Real observed, time-varying costs wipe away most profits; profitability is reported mainly in a period of managed exchange rates. This is not an EUR/USD candidate, but directly supports realistic cost sensitivity.
- Neely & Weller (2003), “Intraday technical trading in the foreign exchange market”, *Journal of International Money and Finance* 22(2), 223–237, DOI 10.1016/S0261-5606(02)00101-8. Genetic-program and optimized-linear rules are selected in-sample and assessed out-of-sample; the authors find no excess returns after realistic transaction costs and trading hours, while some patterns are stable. Use as an anti-overfitting control.



## LIT-008 — Dempster et al. (2001): intraday technical-indicator ensemble and learning

**Publication:** M. A. H. Dempster, Tom W. Payne, Yazann Romahi & G. W. P. Thompson, “Computational Learning Techniques for Intraday FX Trading Using Popular Technical Indicators”, *IEEE Transactions on Neural Networks*, 12(4), July 2001, pp. 744–754. DOI: 10.1109/72.935088.

**Primary full-text PDF:** https://www.jbs.cam.ac.uk/wp-content/uploads/2020/08/wp0030-1.pdf

**Exact source setup**
- GBP/USD tick data aggregated to 15-minute OHLC bars; 1994-01 through 1998-01.
- Rolling evaluation: one year of training followed by one month OOS, rolled forward for 48 OOS months.
- Eight indicator families provide paired buy/sell bits (16 binary inputs): Price Channel Breakout, Adaptive Moving Average, RSI, Stochastics, MACD, Moving Average Crossover, Momentum Oscillator, and CCI.
- The GA represents a rule as a Boolean tree over indicator bits using AND/OR/XOR, maximum depth 4; population 250, 100 generations, 75% crossover / 25% mutation. It learns a stateful long-GBP / neutral decision, not a one-shot CALL/PUT.
- Reinforcement learning, Markov-chain linear programming, and a heuristic are compared with the GA.
- The heuristic uses expected forward return over horizon ell conditioned on the current indicator state; buys above threshold b and sells below threshold x. Parameters are fitted in-sample.
- OOS average annual returns in Table I: at 0 bp, RL 93.8%, GA 94.5%, LP 96.8%, heuristic 96.3%; at 1 bp, RL 16.3%, GA 21.6%, LP 15.9%, heuristic 8.56%; at 4 bp, RL -1.55%, GA 1.67%, LP -1.76%, heuristic -5.03%; at 8 bp, values range from -4.89% to +1.64%; at 10 bp, from -5.63% to +1.71%.
- Authors conclude none of the methods produced significant profits at realistic transaction costs; heuristic strongly overfit; GA generalization constraint helped OOS performance. Indicators used by GA varied with slippage: RSI gained importance as costs increased, while price-channel breakout, stochastics and MA crossover were prominent at zero cost.
- This paper's return metrics are not directional accuracy or binary-option WR. The market is GBP/USD, and the position switching logic differs from our fixed-expiry instrument.

**HydraAI use**
- Do not copy the reported 21.6% annual return as an EUR/USD or binary-option result.
- The most useful contribution is a disciplined way to combine multiple indicator states and constrain rule complexity. A Hydra adaptation could use the eight signal families as candidate inputs, but it must be a separately registered model, trained only on TRAIN, with feature/state definitions frozen before VALIDATION/TEST.
- Do not build an unconstrained combinatorial sweep. The paper explicitly demonstrates overfit risk and cost sensitivity. Our event-based binary scoring, payout, non-overlap and inversion protocol remain separate.

## LIT-009 — Wiśniewska (2014/2015): EUR/USD M1 price reversal and moving-average deviations

**Publication:** Marta Wiśniewska, “EURUSD Intraday Price Reversal”, *Folia Oeconomica Stetinensia*, 14(2), 2014, pp. 152–162. DOI: 10.1515/foli-2015-0014.

**Primary full-text PDF:** https://bazhum.muzhp.pl/media/texts/folia-oeconomica-stetinensia/2014-tom-1422-numer-2/folia_oeconomica_stetinensia-r2014-t1422-n2-s152-162.pdf

**Exact source extraction**
- EUR/USD one-minute LastBid data covering 2004–2006. The paper separately discusses bid/ask for the long/short spot calculations.
- Moving-average windows tested: 60, 120, 180, 240, 300, 360, 720 minutes; 24h, 48h, 72h; 4 days and 5 days.
- ADF test with drift gives p-values about 0.0091–0.0094 at 10/20/60 lags; without drift, p-values about 0.1525–0.1566. The stationarity result is conditional on including a drift.
- The deviation distributions around short moving averages are fat-tailed (e.g. excess-tail kurtosis values shown in Table 4); deviations have means/medians close to zero.
- Trading analysis opens hypothetical long or short spot positions at each of 24 hourly start points and computes the maximum favorable return available at any minute over the next 24 hours. Average maxima are similar for long and short: 0.005525 and 0.006046 in the paper's price-difference units.
- This is a hindsight maximum-excursion analysis, not a tradable signal with a pre-specified exit or fixed expiry. The paper explicitly notes that some maximum returns are negative and asks for shorter-horizon and robustness studies; it also warns that changing the OTC quote provider may matter.

**HydraAI assessment**
- This is useful evidence that M1 EUR/USD deviations from moving averages and possible intraday mean reversion deserve investigation, but it does not specify a validated entry threshold or a forward expiry.
- The 24-hour maximum-return results are not WR and cannot be converted into CALL/PUT accuracy.
- Candidate research hypotheses (not source-faithful replications) may be registered separately: (a) price deviation from rolling mean normalized by rolling volatility; (b) same deviation plus higher-timeframe trend-state exclusion; (c) exact inverse on identical event timestamps. All thresholds and expiry choices must be selected on TRAIN only and frozen before VALIDATION.
- Do not infer the best lookback solely from Table 3 fit/R²; a high R² of price level on moving average is not evidence of predictive trading edge.



| LIT-010 | Adaptive multi-frequency indicator ensemble using genetic programming — Dempster & Jones (2001) | USD/GBP spot FX tick data, 1994–1997, aggregated to intraday frequencies | Abstract reports the best adaptive rule modestly but significantly profitable after realistic transaction costs; individual indicators were generally loss-making. Exact performance and rule ledger not available from accessible abstract. | **PROMISING METHOD; SOURCE AUDIT REQUIRED** — adaptive rule portfolio with periodic re-selection and feedback; not a ready-made binary signal and no published WR. |
| LIT-011 | FX channel-pattern classification — Dempster & Jones (2002) | USD/GBP spot FX tick data, 1989–1997 | Abstract reports statistically significant links between detected channel attributes and profitability; does not provide a binary WR or full rule specification in accessible record. | **PATTERN FAMILY LEAD** — full paper is access-restricted; exact channel geometry, entry/exit, costs and OOS protocol remain unverified. |
| LIT-012 | Opening Range Breakout (ORB) — Holmberg, Lönnbark & Lundström (2013) | Intraday commodity futures (crude oil futures, not FX) | Tests threshold-based ORB using joint distribution of open/high/low/close; abstract reports higher returns and success rate than a fair-game benchmark. Exact result metrics/specification need full-text audit. | **NON-FX METHOD REFERENCE** — do not transfer its reported success to EUR/USD. Potentially useful only as a separately labelled session-breakout hypothesis after independent Hydra validation. |

## LIT-010 — Dempster & Jones (2001): adaptive genetic-programming FX system

**Publication:** M. A. H. Dempster & C. M. Jones, “A real-time adaptive trading system using genetic programming”, *Quantitative Finance*, 1(4), 2001, pp. 397–413. DOI: 10.1088/1469-7688/1/4/301.

**Sources**
- Publisher record: https://www.tandfonline.com/doi/abs/10.1088/1469-7688/1/4/301
- RePEc abstract and bibliographic record: https://ideas.repec.org/a/taf/quantf/v1y2001i4p397-413.html
- Cambridge author publication listing: https://www.statslab.cam.ac.uk/~mrt31/CFR/people/michaeldempsterpublications.html

**What is verified**
- The study follows earlier work in which popular technical indicators used individually were generally loss-making.
- It combines rules based on multiple indicators calculated at different frequencies and lags.
- An initial portfolio of rules is selected using a genetic algorithm on USD/GBP spot FX tick data from 1994–1997, aggregated to intraday frequencies.
- The genetic algorithm is subsequently re-run at regular intervals on out-of-sample data to generate new rules; a feedback system rebalances the rule portfolio. This is a two-level adaptive architecture.
- The abstract reports that the best rule found was modestly, but significantly, profitable after realistic transaction costs.

**Limitations / HydraAI interpretation**
- The accessible abstract does not expose the exact indicator list, tree constraints, rebalance interval, cost schedule, full OOS ledger or numerical effect size. Do not invent these details.
- Market is USD/GBP, not EUR/USD; source strategy is adaptive position/rule-portfolio logic, not fixed-expiry CALL/PUT.
- This is a method worth investigating, not evidence of a 57%+ binary WR.
- If implemented as a Hydra research model, fit candidate rules on TRAIN only, freeze the selection protocol, and simulate periodic re-selection only using data available at each historical decision time. Keep an untouched forward period for prospective validation; avoid letting the genetic algorithm see future labels.

## LIT-011 — Dempster & Jones (2002): channel-pattern FX trading

**Publication:** M. A. H. Dempster & C. M. Jones, “Can channel pattern trading be profitably automated?”, *The European Journal of Finance*, 8(3), 2002, pp. 275–301. DOI: 10.1080/13518470110052831.

**Sources**
- RePEc record and abstract: https://ideas.repec.org/a/taf/eurjfi/v8y2002i3p275-301.html
- Publisher record: https://www.tandfonline.com/doi/abs/10.1080/13518470110052831

**What is verified**
- The authors construct a sample of channel patterns using pattern-recognition algorithms applied to USD/GBP spot FX tick data from 1989–1997.
- They statistically analyze channel attributes to classify patterns that may be traded profitably with simple trading rules.
- The accessible abstract reports statistically significant links between channel attributes and profitability.

**Limitations / HydraAI interpretation**
- Full text is access-restricted in the accessible record. Exact channel construction, feature definitions, thresholds, entry/exit rules, costs, train/test protocol and effect sizes are not verified.
- Statistical association between pattern attributes and profitability is not itself a tradable binary-option win rate.
- Register as a pattern-family lead only. No implementation or promotion until the full specification can be recovered. If a proxy is later defined, label it as a Hydra adaptation and test its exact inverse on identical event timestamps.

## LIT-012 — Holmberg, Lönnbark & Lundström (2013): Opening Range Breakout

**Publication:** “Assessing the profitability of intraday opening range breakout strategies”, *Finance Research Letters*, 10(1), 2013, pp. 27–33. DOI: 10.1016/j.frl.2012.09.001.

**Sources**
- Publisher abstract: https://www.sciencedirect.com/science/article/pii/S1544612312000438
- Umeå University full-text record: https://www.diva-portal.org/smash/get/diva2%3A1521889/FULLTEXT01.pdf

**What is verified**
- The study evaluates mechanical Open Range Breakout rules that enter only after price moves beyond a predetermined threshold.
- The abstract describes a method based on normally distributed returns and the joint distribution of low, high, open and close over a chosen horizon.
- It reports returns significantly above zero and a higher success rate than a fair-game benchmark.
- The study is about crude-oil futures, not EUR/USD FX. The abstract alone does not provide enough detail to reproduce exact range duration, threshold, exit or numerical success rate.

**HydraAI interpretation**
- This is not direct evidence for EUR/USD or binary options.
- A session-range breakout can be considered only as a separately labelled hypothesis. Define session, range window, breakout buffer, entry timing and expiry before TRAIN testing; do not import the paper's reported success rate.
- Because ORB signals cluster around session opens and volatility bursts, report event counts and dependence by day/session, and use non-overlapping outcomes.

- 2026-11-11: added LIT-010 adaptive genetic-programming FX system, LIT-011 channel-pattern FX study, and LIT-012 crude-oil ORB study. Explicitly separated verified abstract-level facts from unavailable full-text parameters; no reported result was converted to binary WR and no candidate promoted.


| LIT-013 | Adaptive Strongly Typed Genetic Programming on M1 FX — Manahov, Hudson & Gebka (2014) | M1 data, EUR/USD plus five other major FX pairs | Abstract reports statistically and economically significant excess returns after transaction costs; STGP outperforms traditional econometric forecasting models in the study. | **HIGH-PRIORITY SOURCE AUDIT** — direct EUR/USD M1 and adaptive rule learning, but no exact WR; full formulas, sample dates, costs and reproducible rule definitions must be extracted before any adaptation. |
| LIT-014 | After-jump momentum using Lee–Mykland L-estimator — Fičura (2019) | EUR/USD, GBP/USD, USD/CHF, USD/JPY; 1m, 5m, 15m, 30m, 1h, 4h, 1d; FX data 1999–2015 | EUR/USD OOS: 30m 682 trades, profit 30,999, drawdown ratio 0.3268; 15m 1,022 trades, profit 34,545, ratio 0.4312; 5m 1,229 trades, profit 12,856, ratio 0.1101; 1m 3,503 trades, loss -50,517. Includes 1-pip spread+commission. Metrics are spot strategy profits, not WR. | **TOP RESEARCH CANDIDATE FOR ADAPTATION** — exact jump detector and OOS design recovered. The source optimizes hold horizon on TRAIN and trades jump direction; binary fixed-expiry conversion is new. Prioritize 15m/30m research, with 5m as secondary; do not extrapolate 15m/30m spot returns to M1 binary options. |
| LIT-015 | Technical indicators on intraday EUR/USD — Mastný (2004) | EUR/USD, 5m/15m/30m/60m; SMA, weighted/variable MA, RSI, MACD | Most indicator variants did not outperform buy-and-hold; strongest results often occurred at 60m, not the shortest timeframe. | **NEGATIVE CONTROL** — useful evidence against assuming a short-period parameter or indicator is universally optimal; no ready binary strategy. |

## LIT-013 — Manahov, Hudson & Gebka (2014): adaptive genetic programming on one-minute FX

**Publication:** Viktor Manahov, Robert Hudson & Bartosz Gebka, “Does high frequency trading affect technical analysis and market efficiency? And if so, how?”, *Journal of International Financial Markets, Institutions and Money*, 28 (2014), pp. 131–157. DOI: 10.1016/j.intfin.2013.11.002.

**Sources**
- Publisher abstract: https://www.sciencedirect.com/science/article/pii/S1042443113000954
- Newcastle University publication record: https://eprints.ncl.ac.uk/196455
- Hull repository record: https://hull-repository.worktribe.com/output/524135

**Verified abstract-level facts**
- Uses real one-minute FX data for EUR/USD, USD/JPY, GBP/USD, AUD/USD, USD/CHF and USD/CAD.
- Applies an adaptive form of Strongly Typed Genetic Programming (STGP) to learn trading/forecasting rules.
- Compares STGP with parametric and non-parametric models using in-sample and out-of-sample forecast and investment-return tests.
- The abstract reports STGP significantly outperforming traditional econometric models and statistically/economically significant excess returns after appropriate transaction costs.

**Limitations / HydraAI interpretation**
- Accessible full-text record was not available in this audit. Sample dates, quote source, exact transaction costs, grammar/functions, fitness objective, re-optimization schedule, OOS metrics by pair and trade ledger remain unverified.
- This is a strong direct-market/method lead, not a reported binary-options WR.
- Before implementation, recover full paper and exact STGP setup. If a proxy is constructed, fit only on TRAIN, freeze the grammar and model-selection protocol before VALIDATION, and evaluate paired inversion on identical event times.

## LIT-014 — Fičura (2019): after-jump momentum with non-parametric L-estimator

**Publication:** Milan Fičura, “Profitability of Trading in the Direction of Asset Price Jumps - Analysis of Multiple Assets and Frequencies”, *Prague Economic Papers*, 28(4), 2019, pp. 385–401. DOI: 10.18267/j.pep.703.

**Primary full text (author working-paper version):** https://quantitative.cz/wp-content/uploads/2018/09/profitability-of-trading-in-the-direction-of-asset-price-jumps-analysis-of-multiple-assets-and-frequencies-milan-ficura-2017.pdf  
**Published journal record:** https://pep.vse.cz/artkey/pep-201904-0001_profitability-of-trading-in-the-direction-of-asset-price-jumps-analysis-of-multiple-assets-and-frequencies.php

**Exact method extracted**
- FX dataset covers 1999-11-01 to 2015-06-12, from forexhistorydatabase.com; pairs EUR/USD, GBP/USD, USD/JPY and USD/CHF.
- Tests seven frequencies: M1, M5, M15, M30, H1, H4 and D1.
- Detects price jumps using the Lee–Mykland (2008) non-parametric L-estimator: returns normalized by local volatility estimated from realized bipower variation. A jump is flagged when the normalized return exceeds a selected extreme-value quantile.
- At a detected jump, enters in the direction of the jump at the close of that bar.
- Holds for a fixed number of bars h, chosen from {1,2,4,8,16}. The local-volatility lookback k is chosen from {4,8,16,32,64,128,256}; confidence threshold p from {0.9,0.95,0.99,0.999}. These parameters are selected by grid search on the first 50% of the sample; the last 50% is OOS.
- Includes 1 pip per-trade spread + commission for FX.
- EUR/USD Table 3 OOS: M30 selected k=32, p=0.95, h=16; 682 trades; profit 30,999; max DD -11,741; drawdown ratio 0.3268. M15: k=64, p=0.90, h=16; 1,022 trades; profit 34,545; max DD -9,916; ratio 0.4312. M5: k=128, p=0.999, h=16; 1,229 trades; profit 12,856; max DD -14,457; ratio 0.1101. M1: k=64, p=0.999, h=1; 3,503 trades; loss -50,517; max DD -51,192; ratio -0.1221.
- The paper explains that M1 produces many small jumps with insufficient predictive power to cover trading costs; M15/M30 are its strongest frequencies for EUR/USD. M5 is positive but materially weaker.
- These profits and drawdown ratios are spot-trading metrics, not accuracy or binary-option WR. The OOS is the second chronological half, but the parameter search is extensive and only one historical split is reported.

**HydraAI assessment / adaptation protocol**
- This is the most concrete short-horizon EUR/USD lead found in this round: exact jump detector, thresholds, entry and holding logic, costs, chronological split, and OOS trade counts are available.
- However, the paper's best EUR/USD holds are 16 bars: 4 hours on M15 or 8 hours on M30. That is not a Pocket Option short expiry. Its positive M5 configuration also holds 16 bars (80 minutes), while its M1 version loses after costs.
- Therefore do not port the published 15m/30m returns as a binary signal. Register a distinct adaptation: detect a jump using only completed bars, enter no earlier than the next executable quote/bar, and test predeclared binary expiries separately. Do not tune the expiry on TEST.
- Test exact inversion on identical jump timestamps and entry/expiry schedule. Also report event clustering, session dependence, overlap handling and sample count. The binary adaptation may fail even if the source spot strategy worked.

## LIT-015 — Mastný (2004): intraday EUR/USD indicator comparison

**Publication:** Václav Mastný, “Performance of technical indicators in forecasting high-frequency foreign exchange rates”, *Acta Universitatis Agriculturae et Silviculturae Mendelianae Brunensis*, 52(3), 2004, pp. 157–166. DOI: 10.11118/actaun200452030157.

**Source:** https://acta.mendelu.cz/artkey/acu-200403-0015_performance-of-technical-indicators-in-forecasting-high-frequency-foreign-exchange-rates.php

**Verified facts**
- Tests simple, weighted and variable moving averages, RSI and MACD on EUR/USD at 5-, 15-, 30- and 60-minute frequencies.
- Each indicator is tested across multiple parameter settings in a simple trading model and compared with buy-and-hold.
- The abstract concludes that parameters optimized at one frequency do not necessarily transfer to another; most of the strongest returns were at 60-minute frequency, and with few exceptions individual indicators did not beat buy-and-hold.

**HydraAI interpretation**
- A useful negative control: do not assume an indicator setting that looks good on M1 must work on M5, or vice versa.
- Not a ready fixed-expiry binary strategy. Exact full-paper trade definitions and parameter table should be extracted only if this control becomes necessary.

- 2026-11-11: added LIT-013 (Manahov et al. adaptive STGP on M1 FX), LIT-014 (Fičura after-jump strategy with full parameter/OOS table), and LIT-015 (Mastný indicator-frequency comparison). LIT-014 is flagged as the strongest concrete EUR/USD M15/M30 research lead, with an explicit warning that spot-horizon results do not establish binary-option WR. No candidate promoted.


| LIT-016 | FX benchmark-fixing intraday reversal — Krohn, Mueller & Whelan (2024) | G9 currencies including EUR/USD; high-frequency quotes 1999–2019 | Strong statistically significant W-shaped dollar return pattern around Tokyo, ECB and London fixes; EUR row: −1.80 bps pre-Tokyo, +2.34 post-Tokyo, −3.53 pre-ECB, +0.63 ECB-to-London, +2.73 post-London. Crucially, authors find client trading returns become significantly negative after transaction costs. | **MARKET MICROSTRUCTURE / FILTER HYPOTHESIS ONLY** — do not treat raw reversal pattern as directly tradable. Fix windows and DST/session calendar could be used as regime labels; executable binary edge unproven. |
| LIT-017 | Dynamic-trigger abnormal daily moves and intraday continuation/reversal — Caporale & Plastun (2020) | EUR/USD and four other FX pairs; daily and hourly data, 2008–2018 | Abnormal daily moves are followed by intraday movement in the same direction during that day, then movement in the opposite direction on the following day; authors report abnormal-profit strategies. | **TWO-HORIZON HYPOTHESIS** — same-day continuation vs next-day reversal. Not M1/M5; dynamic trigger threshold and trading simulation details must be reproduced from full text before adapting. |
| LIT-018 | Reliability of FX jump-detection procedures — (2022) | 11 FX pairs including EUR/USD; 1m, 5m, 15m, 30m, 60m; 2010–2016 | BNS and Ait-Sahalia–Jacod methods detect materially different jump counts across frequencies; for EUR/USD BNS counts 1,433 (1m), 1,216 (5m), 1,258 (15m), 1,433 (30m), 1,336 (60m), while AJ counts 1,242, 1,332, 1,301, 1,242, 1,279 respectively. | **METHODOLOGY CONTROL FOR LIT-014** — jump labels are detector- and frequency-dependent; require robustness across at least two detectors and frozen thresholds. Not a trading strategy. |

## LIT-016 — Krohn, Mueller & Whelan (2024): FX fixing return reversals

**Publication:** Ingomar Krohn, Philippe Mueller & Paul Whelan, “Foreign Exchange Fixings and Returns around the Clock”, *The Journal of Finance*, 79(1), 2024, pp. 541–578. DOI: 10.1111/jofi.13306. First published online 18 December 2023.

**Primary source (open access):** https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13306

**Verified source details**
- High-frequency indicative bid/ask quotes from Refinitiv Tick History for G9 currencies including EUR/USD, January 1999–December 2019; tick-by-tick data.
- The paper identifies systematic dollar appreciation before and depreciation after Tokyo, ECB/Frankfurt and London fixes.
- Fixing times used in the paper: Tokyo 09:55 local; ECB 14:15 Frankfurt local; London 16:00 London local. Its main tables use Eastern Time windows, so any Hydra session calendar must convert dates with daylight-saving transitions rather than hard-code one UTC offset.
- EUR row of Table I reports average returns (bps): pre-Tokyo −1.80 (t=−8.84); post-Tokyo +2.34 (t=9.29); pre-ECB −3.53 (t=−7.25); ECB-to-London +0.63 (t=1.36, not significant at conventional levels); post-London +2.73 (t=6.78).
- The pattern is tied to the publication/existence of reference fixes; natural experiments using Japanese holidays and pre-fix eras support this interpretation.
- The authors link the pattern to inventory risk and unconditional client demand for USD around fixes; reversals are larger in high-volatility/high-order-imbalance states.
- Critical tradability caveat: the paper explicitly finds that the unconditional pattern cannot easily be arbitraged in the client market; transaction-cost-adjusted client returns are significantly negative, while liquidity-provision returns are positive.

**HydraAI interpretation**
- This is a strong EUR/USD intraday market-structure result, but not a simple directional strategy for a retail binary-options account.
- Do not convert the table's average bps into binary WR. It is an average return pattern over broad windows, not per-entry fixed-expiry outcomes.
- Potential use: add fix-window/session labels as explanatory features or as a pre-registered market-regime filter for other candidates, then test whether candidate performance changes around the fixes. Do not trade the fixing reversal blindly.
- Any test must use correct historical local-time/DST conversion, exclude/flag holidays when the relevant fix is not published, and include realistic Pocket Option payout/quote limitations. No candidate promotion from this paper alone.

## LIT-017 — Caporale & Plastun (2020): abnormal daily FX moves

**Publication:** Guglielmo Maria Caporale & Alex Plastun, “Daily abnormal price changes and trading strategies in the FOREX”, *Journal of Economic Studies*, 48(1), 2021, pp. 211–222. DOI: 10.1108/JES-11-2019-0503. Published online/accepted 2020.

**Primary full-text PDF:** https://bura.brunel.ac.uk/bitstream/2438/20567/5/FullText.pdf  
**Repository record:** https://dspace.brunel.ac.uk/handle/2438/20567

**Verified method/results**
- EUR/USD, USD/JPY, USD/CAD, AUD/USD and EUR/JPY; daily and hourly MetaQuotes data, 2008-01-01 to 2018-12-31.
- Abnormal daily moves are detected with a dynamic trigger: average return plus/minus a threshold expressed in standard deviations. Returns are computed from daily open to close to reduce gap distortions.
- For EUR/USD, the paper reports statistically significant differences between hourly intraday dynamics on abnormal-move days and normal days. Positive abnormal days show significant effects in most European and US sessions and half of the Asian session; negative abnormal moves show strongest volatility in the US session.
- Cumulative abnormal returns rise in the direction of the abnormal move during the same day; the average time at which the abnormal move becomes detectable is 19:00 for positive moves and 17:00 for negative moves (paper's time convention).
- The abstract/conclusion report same-day continuation and opposite-direction movement on the following day; authors report trading simulations with abnormal profits.

**HydraAI interpretation and limits**
- This suggests a two-stage hypothesis: continuation after an abnormal daily move within the same day, then reversal on the following day. These are different horizons and must be registered separately.
- Source uses daily abnormal triggers and hourly intraday returns, not M1/M5 micro-signals. It cannot establish short expiry WR.
- Recover exact standard-deviation multiplier, rolling estimation window, trading entry/exit, session schedule and costs from the full PDF before reproducing. Do not choose these parameters from Hydra TEST.
- A binary adaptation must test both directions: continuation and exact inversion, with identical event timestamps; expiry must be separately predeclared.

## LIT-018 — FX jump-detection robustness (2022)

**Publication:** “The jump dynamics of foreign exchange rates: how reliable and consistent are the results of widely utilized jump detection procedures”, *Heliyon*, 8(10), 2022, e10909. DOI: 10.1016/j.heliyon.2022.e10909.

**Primary open-access source:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9563180/  
**Publisher record:** https://www.sciencedirect.com/science/article/pii/S2405844022021971

**Verified facts**
- Compares BNS (Barndorff-Nielsen–Shephard) and AJ (Aït-Sahalia–Jacod) jump tests on 11 currency pairs, including EUR/USD, from 2010-01-01 to 2016-12-31.
- Uses indicative bid/ask quotes and midpoint log-prices at 1m, 5m, 15m, 30m and 60m frequencies.
- Jump detection is based on a 95% significance level. The authors report that jump counts vary materially with both detector and sampling frequency.
- For EUR/USD, Table 1 gives BNS counts 1,433 / 1,216 / 1,258 / 1,433 / 1,336 for 1m / 5m / 15m / 30m / 60m, and AJ counts 1,242 / 1,332 / 1,301 / 1,242 / 1,279.
- For EUR/USD at 5m, BNS identifies 1,216 jump intervals out of 735,264 (about 0.165%); the number of jump days is much higher because at least one jump can occur on a day.
- The paper also examines links between jumps and scheduled macroeconomic announcements.

**HydraAI interpretation**
- This is a methodological control for LIT-014: a jump is not an objective label independent of sampling frequency and statistical detector.
- If we test jump-following or jump-reversal candidates, compare at least two defensible detection methods (e.g. Lee–Mykland vs BNS/AJ where implementable), record disagreement, and freeze detector/thresholds before VALIDATION.
- Do not optimize the detector by selecting whichever one yields the best TEST WR. No standalone trading edge is claimed by this paper.

- 2026-11-11: added LIT-016 (FX fixing reversals), LIT-017 (abnormal daily move continuation/next-day reversal), and LIT-018 (jump-detector robustness). Key distinction recorded: fixing pattern is statistically strong but client returns are negative after costs; jump labels vary by method/frequency. No candidate promoted.
