# Pre-release EUR/USD M1 study: do moves begin before scheduled US releases?

**Date:** 2026-11-09  
**Branch:** `hydra/research-validation`  
**Dataset:** `eurusd_research_clean.csv` (486,488 rows; 2025-07-21 through 2026-11-05 UTC)  
**Sample:** 62 scheduled release observations, 186 matched control windows.

## Main conclusion

**There is no consistent market-wide directional drift before the releases.** Across all 62 event observations, the median signed move in the final 30 minutes before publication was only +0.10 pips, and 50.0% of those windows closed above their opening price. Matched ordinary weekdays showed +0.30 pips and 47.5% positive. In the final 15 minutes, event windows were positive 43.5% of the time versus 50.5% for controls.

However, the category breakdown reveals two hypotheses worth further investigation:

1. **Before FOMC rate decisions**, the final 30 minutes were positive on 8 of 11 occasions (72.7%), versus 4 of 11 (36.4%) for the matched-control medians. Median signed move: +2.20 pips versus -0.90 pips. This is the clearest pre-release directional difference in this sample, but n=11 is small and the result may be sensitive to individual meetings or the selection of this interval.
2. **Before FOMC minutes**, the hour before publication was unusually weak: only 2 of 10 event windows were positive (20.0%) over 60 minutes, compared with 33.3% for controls. Median signed move was -7.90 versus -3.25 pips. This is a candidate downside-skew, not yet an entry signal.

NFP also showed negative pre-release movement, while CPI did not. PPI displayed a possible reversal structure: relatively weak movement in the final 30 minutes before publication, followed in the previous event study by a positive 30-minute post-release sign on 9 of 14 dates. That sequence needs event-by-event verification and must not be interpreted as a guaranteed reversal.

## Results by event category

All price changes are pips. “Path” is the sum of absolute one-minute close-to-close changes; “signed” is the last close minus the first candle open. Control values are medians of the three matched control dates per event, then summarized across events.

| Event | n | Window | Event path / control | Event signed / control | Positive event windows / controls |
|---|---:|---|---:|---:|---:|
| CPI | 14 | -60 to 0 min | 37.05 / 40.80 | +2.00 / +1.85 | 64.3% / 59.5% |
| CPI | 14 | -30 to 0 min | 18.15 / 21.00 | +0.60 / +1.60 | 71.4% / 64.3% |
| CPI | 14 | -15 to 0 min | 7.80 / 9.30 | -0.20 / +0.65 | 50.0% / 57.1% |
| NFP | 13 | -60 to 0 min | 37.30 / 39.30 | -2.20 / +0.80 | 38.5% / 56.4% |
| NFP | 13 | -30 to 0 min | 16.60 / 21.40 | -1.30 / +0.70 | 38.5% / 46.2% |
| NFP | 13 | -15 to 0 min | 8.00 / 10.20 | -0.10 / 0.00 | 46.2% / 46.2% |
| PPI | 14 | -60 to 0 min | 46.30 / 40.50 | -2.80 / -0.90 | 50.0% / 40.5% |
| PPI | 14 | -30 to 0 min | 22.70 / 20.20 | -2.95 / +0.70 | 35.7% / 47.6% |
| PPI | 14 | -15 to 0 min | 10.00 / 9.25 | -1.70 / +0.10 | 35.7% / 59.5% |
| FOMC statement | 11 | -60 to 0 min | 58.20 / 57.70 | -1.40 / +0.20 | 45.5% / 48.5% |
| FOMC statement | 11 | -30 to 0 min | 29.70 / 27.10 | +2.20 / -0.90 | 72.7% / 36.4% |
| FOMC statement | 11 | -15 to 0 min | 13.30 / 13.90 | +1.60 / -0.70 | 63.6% / 39.4% |
| FOMC minutes | 10 | -60 to 0 min | 57.90 / 60.70 | -7.90 / -3.25 | 20.0% / 33.3% |
| FOMC minutes | 10 | -30 to 0 min | 26.15 / 25.65 | -2.60 / -0.65 | 30.0% / 40.0% |
| FOMC minutes | 10 | -15 to 0 min | 12.95 / 12.85 | -2.55 / -1.35 | 20.0% / 46.7% |

## Pooled result across all event categories

| Pre-release interval | Event median path | Control median path | Event median signed move | Event positive share | Control positive share |
|---|---:|---:|---:|---:|---:|
| -60 to 0 min | 46.70 | 46.10 | -1.15 | 45.2% | 48.9% |
| -30 to 0 min | 20.85 | 22.60 | +0.10 | 50.0% | 47.5% |
| -15 to 0 min | 9.80 | 10.90 | -0.45 | 43.5% | 50.5% |
| -60 to -30 min | 25.65 | 21.70 | -0.65 | 45.2% | 56.0% |
| -30 to -15 min | 11.15 | 11.70 | +0.45 | 51.6% | 45.9% |

The pooled sample does not show a broad directional lead-in. The strongest pooled difference is somewhat greater path activity in the -60 to -30 minute segment, but it is not accompanied by a reliable direction. The final 15 minutes are, if anything, less often positive than control windows.

## Method

- Release times are New York local time, converted to UTC with the DST-aware `America/New_York` timezone.
- BLS CPI, NFP and PPI releases are tested at 08:30 ET; FOMC statements and minutes at 14:00 ET.
- Windows are measured backward from the scheduled release: -60 to 0, -30 to 0, -15 to 0, plus non-overlapping segments -60 to -30 and -30 to -15.
- A window is included only when every one-minute candle is present.
- For each event, controls are drawn from the same weekday within +/-35 calendar days, excluding all dates in the event ledger. The three closest controls are selected by similarity of the earlier baseline path from -180 to -120 minutes. This baseline is separate from the pre-release windows being tested.
- 62 events had complete windows; 3 controls per event were retained, yielding 186 control observations.

## Interpretation and limitations

1. The apparent FOMC-statement pre-release rise is the most interesting result. It could reflect positioning, repricing, or unrelated market conditions. The study does not establish that the market “knows” the decision in advance.
2. FOMC minutes are not equivalent to rate decisions. The observed negative skew may relate to the particular macro regime or the contents of the minutes; the calendar timestamp alone does not explain it.
3. NFP's negative pre-release median is consistent with the downside skew seen in the prior post-release study, but the final 15-minute direction is nearly balanced. This is not a clean timing rule.
4. PPI's negative final 30-minute skew followed by a positive post-release sign in the previous study is worth examining as a possible reversal. The sample is small and the post-release direction is not an executable trade outcome.
5. These are candle close/open movements, not Pocket Option wins. Spread, quote side, entry latency, payout, and expiry settlement are not modeled.
6. The windows overlap by design (for example, -30 to 0 includes -30 to -15 and -15 to 0). They must not be counted as independent samples.
7. There are only 10–14 observations per category. No p-value or confidence interval here would make this exploratory sample a validated edge; multiple intervals and categories were examined.

## Decision for HydraAI

Do **not** add a pre-news CALL/PUT rule to HydraAI. Keep the findings as research hypotheses only.

Next test should be event-by-event and chronological:
- inspect whether the FOMC pre-release rise is concentrated in a few meetings or stable across them;
- compare the pre-release trend with the actual post-release reaction for each individual event;
- condition on the actual surprise versus consensus for CPI/NFP/PPI and on rate decision versus market pricing for FOMC;
- lock entry and expiry conventions, then test only on a later holdout period with actual per-trade payout assumptions.

## Reproducibility

Script: `research/pre_release_event_study.py`

Run:
```bash
python research/pre_release_event_study.py /path/to/eurusd_research_clean.csv --out research_output
```

It writes `pre_release_event_windows.csv` and `pre_release_matched_controls.csv`.

No production strategy, desktop application code, or automated trading behavior was changed.
