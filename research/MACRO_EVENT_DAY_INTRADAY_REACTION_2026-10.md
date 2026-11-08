# Intraday reaction on Treasury settlement days — October 2026

**Status:** preliminary descriptive M1 replay; not a causal result or trading rule.  
**Branch:** `hydra/research-validation`  
**Input:** repository file `eurusd_history_extended.csv`, 30,048 M1 OHLC rows, 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC.  
**Raw data SHA:** `ee5f264997f94553818d95ced1d3b11fa58737e1`.

## Question

Does EUR/USD already behave differently from the start of the UTC day on Treasury debt settlement dates, or does unusual activity appear only around European / US trading hours?

## Important event classification

This small sample contains **Treasury issuance settlement dates**, not a clean list of Treasury coupon-payment or principal-maturity payout dates. Do not interpret this test as a direct test of cash paid by Treasury to existing bondholders.

Six settlement dates inside the available M1 window were used:
- Oct 13 — bill settlement cluster;
- Oct 15 — settlement of the $119bn 3Y/10Y/30Y coupon-auction issuance plus bill settlements;
- Oct 20 — bill settlement cluster;
- Oct 22 — bill settlement cluster;
- Oct 23 — settlement of the $13bn 20Y reopening;
- Oct 27 — bill settlement cluster.

This is a small event sample, not a complete universe of Treasury payment events.

## Method

- Parsed the raw CSV and retained valid numeric OHLC rows.
- Split each UTC calendar day into four fixed six-hour blocks: 00–06, 06–12, 12–18, 18–24 UTC.
- A block was included only if it contained all 360 M1 rows.
- For each block calculated:
  - signed open-to-last-close return in pips (1 pip = 0.0001);
  - total absolute sum of consecutive M1 close-to-close changes in pips (intraperiod path activity);
  - high-low range in pips.
- Compared the six settlement dates with all other eligible dates in the same short CSV window. These are **unmatched controls**; weekday, news, volatility regime and other confounders are not controlled.
- The first and last partial calendar days and blocks with fewer than 200 rows were not used.

## Result: activity by time of day

Median total absolute M1 close-to-close movement (pips):

| UTC block | Settlement dates (n=6) | Other eligible dates (n=14–15) | Event/control ratio |
|---|---:|---:|---:|
| 00–06 | 193.1 | 160.3 | 1.20x |
| 06–12 | 308.6 | 236.6 | 1.30x |
| 12–18 | 320.7 | 267.3 | 1.20x |
| 18–24 | 175.6 | 197.9 | 0.89x |

Median six-hour high-low range (pips):

| UTC block | Settlement dates | Other eligible dates |
|---|---:|---:|
| 00–06 | 25.6 | 12.8 |
| 06–12 | 30.8 | 23.8 |
| 12–18 | 36.8 | 26.1 |
| 18–24 | 14.7 | 15.9 |

**Initial observation:** the largest relative activity difference appears in 06–12 UTC (about +30% in median absolute path movement), with a smaller difference already visible in 00–06 UTC (about +20%). 12–18 UTC is also elevated. 18–24 UTC is not elevated in this sample.

This is consistent with the hypothesis that activity may already be elevated before the US afternoon / settlement processing window. It does **not** establish that the settlement causes the move, or that a trader could predict its direction.

## Direction is not stable

Settlement-day six-hour signed returns (pips):

| Date | 00–06 | 06–12 | 12–18 | 18–24 |
|---|---:|---:|---:|---:|
| Oct 13 | +17.0 | +8.8 | +4.4 | +6.5 |
| Oct 15 | +18.8 | -7.3 | +7.4 | -2.9 |
| Oct 20 | +13.0 | -15.4 | +21.9 | -6.6 |
| Oct 22 | +13.1 | -44.9 | +26.8 | -2.9 |
| Oct 23 | -9.3 | -19.0 | +4.6 | +8.4 |
| Oct 27 | -6.2 | -20.0 | -10.9 | -6.5 |

Direction counts across the six event days:
- 00–06 UTC: 5 up / 1 down;
- 06–12 UTC: 2 up / 4 down;
- 12–18 UTC: 5 up / 1 down;
- 18–24 UTC: 3 up / 3 down.

The direction flips between blocks and across dates. No reliable CALL/PUT bias emerges. Oct 22, for example, had a large early-European decline followed by a substantial US-hours recovery. This is exactly why a daily close comparison is insufficient.

## Interpretation

1. **There is a preliminary volatility/activity clue:** on these six issuance-settlement dates, M1 path activity was higher than on other eligible dates in the 00–18 UTC blocks, most notably 06–12 UTC.
2. The 00–06 UTC difference suggests that any effect need not wait for the European open, but the evidence is only six dates and unmatched controls.
3. **No directional edge:** signs are inconsistent; the result supports investigating event-conditioned volatility / WAIT decisions, not a blind CALL or PUT.
4. The sample's event definition is settlement of new issuance and bill settlements, not principal/coupon cash payments to bondholders. A separate payout-event dataset is required to answer that exact question.
5. The six-day sample is too small to distinguish a genuine event effect from coincident macro releases, normal volatility clustering, weekday/session effects or selection bias.

## Next required experiment

- Build a separate event panel of actual Treasury principal maturities and coupon payment dates, with amounts and precise payment dates, plus comparable euro-area sovereign payments.
- Expand the M1 sample across multiple years (the repository's Dukascopy long-history workflow downloads 2024–2026).
- Match each event block to non-event days with the same weekday and UTC/session block, similar prior 20–60 minute volatility, and exclude overlapping major macro releases or tag them separately.
- Predeclare event windows around the day start, London open and 09:15 New York payment-processing reference; treat 09:15 ET as a reference, not an assumption that all relevant cash flows hit FX at that instant.
- Report effect sizes, confidence intervals and day-cluster bootstrap results. Only after this, test whether an event context improves a frozen CALL/PUT/WAIT strategy on untouched dates.

**Bottom line:** the first M1 replay gives a small, interesting hint of elevated movement beginning before the European session on Treasury issuance-settlement days. It does not yet test actual coupon/principal payout days and does not demonstrate a tradable edge.
