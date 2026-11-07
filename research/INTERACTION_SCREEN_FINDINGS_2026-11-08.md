# Train-only CALL / PUT interaction screen — 2026-11-08

## Reproducibility
- Branch: `hydra/research-validation`
- Commit containing the screen and workflow: `ea005102f934482448322f93b94b1b090780290f`
- GitHub Actions run: [42419698627](https://github.com/Levon4ik026/HydraAI/actions/runs/42419698627)
- Workflow executed existing project tests, research unit tests, winner/loser audit, and this interaction screen; the screen step and both artifact uploads completed successfully.
- Dataset: `eurusd_history_extended.csv`; 30,048 M1 rows; 6,008 complete M5 bars; 2 continuous segments; 2026-10-07 through 2026-10-28.
- Frozen trigger: BB(20,2) re-entry + Williams %R(14) cross; ADX(14) >= 15.
- Execution: signal at closed M5 candle, entry next M5 open, settle at that next M5 close. Payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u.
- 145 signal events: 97 train and 48 chronological holdout. CALL 86 total (54 train, 32 holdout); PUT 59 total (43 train, 16 holdout).

## Frozen base results

| Direction / period | W/L/D | Decisive WR | Net | ROI | PF | Max DD | Max losing streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| CALL train | 29/22/3 | 56.86% | +4.68u | +8.67% | 1.21 | 6.16u | 6 |
| CALL holdout | 23/9/0 | 71.88% | +12.16u | +38.00% | 2.35 | 2.16u | 2 |
| PUT train | 19/21/3 | 47.50% | -3.52u | -8.19% | 0.83 | 5.80u | 4 |
| PUT holdout | 8/8/0 | 50.00% | -0.64u | -4.00% | 0.92 | 3.00u | 3 |

## Discovery protocol and results
Only seven predeclared two-feature interactions were screened, separately for CALL and PUT. Each axis was split at its own TRAIN median into four cells. A cell was eligible only with at least 8 train observations, positive train net, and at least +8 percentage points decisive-WR lift over that direction's train baseline. At most one rule per direction was frozen, ranked by train net per trade, then lift, then sample size. This searched 56 direction/cell combinations; winner's curse / selection bias is therefore material.

### CALL
Frozen train rule: `ema20_50_atr <= -0.43772535` AND `body_range > 0.56454248`.
- Train selected cell: 17 trades, 14W/3L/0D; 82.35% decisive WR; +9.88u; ROI +58.12%; PF 4.29; max DD 3.00u; max losing streak 3.
- Holdout selected cell: 14 trades, 10W/4L/0D; 71.43% decisive WR; +5.20u; ROI +37.14%; PF 2.30; max DD 1.16u; max losing streak 1.
- Holdout coverage: 14/32 CALL signals (43.8%).

### PUT
Frozen train rule: `atr14_close > 0.00029368424` AND `upper_wick_range > 0.19354839`.
- Train selected cell: 11 trades, 8W/3L/0D; 72.73% decisive WR; +4.36u; ROI +39.64%; PF 2.45; max DD 1.08u; max losing streak 1.
- Holdout selected cell: 2 trades, 1W/1L/0D; 50.00% decisive WR; -0.08u; ROI -4.00%; PF 0.92; max DD 1.00u; max losing streak 1.
- Holdout coverage: 2/16 PUT signals (12.5%).

## Verdict
- CALL interaction is a hypothesis worth prospective observation: its train-selected cell retained positive results in this historical holdout, but only 14 holdout trades. The holdout period has already been examined in earlier project research, so it is not genuinely untouched; the 56-cell selection process adds substantial optimism. This is not evidence of a confirmed edge.
- PUT interaction does not generalize: the frozen cell covered only two holdout signals and produced -0.08u. It is not a usable PUT filter.
- Do not alter the desktop math core, claim confirmed profitability, or merge this rule. Keep CALL/PUT separate.
- Next valid step: freeze the CALL candidate exactly as above and observe it prospectively on new, continuous, non-OTC data. Keep all new observations out of tuning; report counts, W/L/D, decisive WR, net at 92%, ROI, PF, drawdown, losing streak, coverage, and uncertainty. Do not treat the historical holdout as independent confirmation.

## Limitations
The sample is small, signal outcomes may be serially dependent, and the screen uses median splits and multiple candidate cells. No block-bootstrap / day-cluster uncertainty interval was computed in this run. The reported win rates and returns are descriptive, not inferential.
