# Research CI repair log — 2026-11-11

## Verified failures and causes

- Long-history run [43016443559](https://github.com/Levon4ik026/HydraAI/actions/runs/43016443559), commit `60de983436f2cce23a51e36c1c17336d382b7faf`, failed in `Run HYDRA Time Machine walk-forward research`.
- The concrete exception was `ValueError: too many values to unpack (expected 7)` at `research/hydra_time_machine.py:167`. The imported `standalone_strategy_screen.summarize()` returns a dictionary, but `choose_validation_variants()` unpacked it as a seven-item tuple. The later portfolio summary path also unpacked the dictionary returned by `summary_outcomes()` as a tuple, so fixing only the first traceback would have exposed a second failure.
- Research validation run [43016296067](https://github.com/Levon4ik026/HydraAI/actions/runs/43016296067), commit `b89afffe293d5bb2f358854ecb219483828219ec`, failed in the train-only interaction screen because the short `eurusd_history_extended.csv` did not span the frozen multi-year TRAIN/VALIDATION/TEST dates. The later `60de983` change added a relative 60/80 split fallback for short datasets while preserving fixed dates whenever full multi-year coverage exists. The current research-validation run on `05c535b` passed, confirming that path is now green.
- Other logged warnings about Node.js 20 deprecation were non-fatal and did not cause either failure.

## Safe repair on research-validation only

- Updated `hydra_time_machine.py` to read the shared summary dictionary by named keys in both validation selection and final portfolio reporting.
- Made a no-decisive-outcome sample report WR as `n/a` instead of raising during formatting.
- Updated the Time Machine unit test to assert the dictionary contract and added a draw-only regression case.
- No strategy rule, threshold, payout, source data, split boundary, or holdout date was changed. No old TEST sample was reclassified as fresh.
- This journal is intentionally separate from `WORK_LOG_*.md`, so the code repair does not trigger another overlapping same-day MEAN_REV forward holdout run.

## Current HEAD before repair

- `hydra/research-validation`: `05c535bf9b7027e000cee00b9ea2db64f081bfab`.
- `hydra/stabilization`: `dce8d011ea7f56d7ff890749243ef7d54f0e1afc`.
- `main`: `b5dc96b089073c72619afafa03428827a92dbbf5`.

The repair is committed only to `hydra/research-validation`. CI is expected to rerun the research validation and long-history validation workflows; their results must be checked separately from any strategy backtest result.
