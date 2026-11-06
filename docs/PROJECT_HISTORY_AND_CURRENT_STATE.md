# HydraAI — Project History and Current State

Last verified: 2026-11-06
Repository: `Levon4ik026/HydraAI`

## 1. Purpose and safety boundary

HydraAI is a local Windows application for EUR/USD M1 market analysis and manual CALL / PUT / WAIT decision support for Pocket Option DEMO.

- Analysis and decision support only.
- No automated trading, order placement, or trade execution.
- Research experiments must remain isolated from the working application.
- Do not treat a backtest result as evidence of live profitability.

## 2. Branch map (verified 2026-11-06)

The following branches exist:
- `main`
- `hydra/research`
- `hydra/research-lab`
- `hydra/stabilization`

GitHub compare results:
- `hydra/research-lab` is 7 commits ahead of `hydra/research`, 0 behind.
- `hydra/research-lab` is 30 commits ahead of `main`, 0 behind.
- The merge base of `hydra/research` and `hydra/research-lab` is `537ee98895667b2930c62291a649d40ff2168369`.
- The `main` head observed during this check was `ed48408e5e3ed75beca546df53f7817c05ba5a72`.

Rules:
- Continue research only on `hydra/research-lab`.
- Do not modify `main` or `hydra/stabilization`.
- Do not copy older GitHub application files over the newer local Windows application without an explicit file-by-file comparison.
- The GitHub repository is not a mirror of the current local application.

## 3. Local application context (reported by owner; not independently inspected in this GitHub check)

Working directory: `C:\\HydraAI_Desktop` on Windows 11.
Hardware: Ryzen 5 5600X, 32 GB RAM, RTX 3070 Ti.
The owner reported a working local state using 200 continuous EUR/USD M1 candles and backup:
`HYDRA_BACKUP_200_20261105_221349`.

Key local modules reported by the owner:
- `main.py` — PySide6 UI and chart.
- `guest_feed_reconnect.py` — Pocket Option guest WebSocket feed, launched as a separate process.
- `hydra_ai_analyzer.py` — Ollama/Qwen analysis.
- `hydra_technical_metrics.py`, `hydra_indicators.py`, `hydra_strategy_core.py`, `hydra_data_quality.py`.

These local files were not present as a complete current application in the GitHub branches inspected. Do not infer their present local state from this document.

## 4. Existing research work on hydra/research-lab

Verified files:
- `research/data_audit.py`
- `research/README.md`
- `research/tests/test_data_audit.py`
- `.github/workflows/research-tests.yml`
- `docs/RESEARCH_AUDIT_2026-11-05.md`
- `research/reports/INITIAL_DATA_AUDIT_2026-11-05.md`

The data audit is standard-library-only. It reports source SHA-256, file size, row count, timestamp range, duplicates, invalid OHLC, flat candles, gaps, weekend rows, source ordering, naive timestamps, and row-level issues. It does not silently repair, reorder, deduplicate, or discard source data.

The research test file contains four unittest test methods. The workflow is configured to run:
`python -m unittest discover -s research/tests -v`
on pushes and pull requests to `hydra/research-lab` when research files or the workflow change.

Important: the existence of the workflow is verified; a successful GitHub Actions run was NOT verified in this check. Do not claim CI is green without inspecting an actual run.

## 5. Historical data already in the repository

The previous research audit records the following for `eurusd_history_extended.csv` on `main`:
- 30,048 rows.
- UTC range: 2026-10-07 04:31 through 2026-10-28 01:19.
- 0 duplicate timestamps.
- 0 invalid OHLC rows under basic positivity and high/low/order checks.
- 17 flat candles.
- 1 minute-series gap: 2026-10-09 22:43 to 22:45 UTC.
- 8,640 rows timestamped Saturday/Sunday in UTC.
- `eurusd_history_extended_progress.csv` had the same blob SHA in that audit and was a duplicate, not an independent dataset.

This is a previously recorded audit result, not a fresh independent re-audit of the large CSV on 2026-11-06. The GitHub file fetch returned no CSV body in the current inspection. Re-fetch or download it before relying on the row-level claims. Weekend timestamps must not be deleted automatically: first establish whether they are OTC, synthetic, or otherwise inconsistent with the intended EUR/USD feed.

A separate local archive reportedly contained `eurusd_history_5000_candidate.csv` with 5,066 candles spanning roughly 84 hours. This is not the only known historical dataset; the repository's extended file is larger.

## 6. Existing backtest findings and limitations

The current `main/backtest_v3.py` was inspected:
- EMA20 / EMA50 + RSI14 signal.
- Horizons: 1, 3, 5, 10 minutes.
- Signal uses the candle's computed indicators; entry is modeled at the next candle Open.
- Exit is modeled at the horizon candle Close.
- Non-overlapping trades.
- 70% / 30% chronological split.
- Payout is hard-coded as `PAYOUT = 0.80`.
- It sorts timestamps and drops duplicates during loading.
- It does not provide the required configurable per-trade or scenario payout.

The existing `main/backtest_split_summary.csv` contains aggregated EARLY and HOLDOUT results for 1, 3, 5, and 10 minute horizons. The recorded HOLDOUT net results are negative:
- 1 min: -169.2 units
- 3 min: -195.8 units
- 5 min: -170.0 units
- 10 min: -190.8 units

These are historical outputs under the old test's assumptions, not approved project benchmarks. The split summary is aggregated and should not be confused with a direction-separated, fully audited research result.

The 2026-11-05 research audit also records an earlier directional summary for a different `backtest_v3_summary.csv` output using the 80% payout assumption. Do not compare results across scripts unless signal rules, data, split, gap policy, execution model, and payout are identical.

A previously discussed CALL 2-minute result at 92% payout was explicitly preliminary and unverified. Do not cite it as a validated edge or integrate it into the app.

## 7. Research requirements already approved by the owner

Research the following families and combinations:
- EMA / SMA
- RSI
- MACD
- ADX / DI
- Bollinger Bands
- ATR
- Keltner Channels
- Stochastic
- CCI
- Supertrend
- Price Action and breakouts
- Multi-vote and regime-aware filters

Required methodology:
1. Use closed candles only; signal is formed after candle close.
2. Model entry at the next available candle Open.
3. Test CALL and PUT separately.
4. Test expirations 1, 2, 3, and 5 minutes (additional horizons may be exploratory but must be labeled).
5. Exclude trades whose signal-to-entry or entry-to-expiry path crosses missing M1 intervals.
6. Model draws explicitly.
7. Make payout configurable; the owner commonly observes around 92%, but actual payout varies. Never hard-code 80% or 92% as universal truth.
8. Report trades, wins, losses, draws, decisive win rate, net profit, expectancy per trade, max drawdown, max losing streak, confidence intervals, and session/hour/regime breakdowns.
9. Use chronological Train / Validation / Holdout and Walk-Forward. Do not tune parameters on Holdout.
10. Compare against baselines on the same timestamps and under the same execution assumptions.
11. Verify indicator calculations and prevent look-ahead bias.
12. Record source SHA-256, config, script version, and reproducible outputs for every experiment.
13. Do not integrate an experimental strategy into the live application until results are independently repeated and validated.

## 8. Known open items

- Re-fetch and independently audit `eurusd_history_extended.csv`; verify exact contents, source provenance, weekends, gaps, candle boundaries, and whether quotes are suitable for the intended Pocket Option EUR/USD instrument.
- Confirm the actual GitHub Actions result for the research test workflow; workflow configuration alone is not proof of passing tests.
- Inspect the full implementation of `analyze_candles` before relying on any legacy backtest path that calls it.
- Build a reproducible backtest engine with configurable payout scenarios, 1/2/3/5-minute horizons, direction-separated results, gap-safe execution, Train/Validation/Holdout, and Walk-Forward.
- Keep the local UI encoding repair separate; do not rewrite `main.py` wholesale or alter the live feed collector without evidence and a narrowly scoped patch.
- Keep version control clean: avoid accumulating untracked patch scripts and redundant backup copies in the repository.

## 9. Working protocol

The owner is not a programmer and prefers minimal, consolidated actions.
- Inspect existing code and prior results before asking the owner to repeat checks.
- Ask for local commands only when the required data cannot be accessed through GitHub or existing files.
- Before modifying code, state the exact scope and reason; preserve a backup or use an isolated branch commit.
- Make small, focused changes. Do not refactor unrelated modules.
- Run available automated tests and report exactly what ran and its result.
- Distinguish verified facts, owner-reported local state, prior audit claims, and unverified hypotheses.
- Never claim an app was launched, a feed connected, or a test passed unless it was actually observed.
- Never enable or implement automatic trading.
