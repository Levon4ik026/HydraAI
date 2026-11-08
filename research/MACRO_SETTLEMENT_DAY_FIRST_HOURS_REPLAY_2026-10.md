# Corrected settlement-day replay: first-hours and session windows

**Status:** preliminary descriptive replay; not causal and not a trading rule.  
**Branch:** `hydra/research-validation`  
**Source file:** `eurusd_history_extended.csv`  
**Blob SHA:** `ee5f264997f94553818d95ced1d3b11fa58737e1`  
**Rows parsed:** 30,048 M1 OHLC rows, 2026-10-07 04:31 UTC to 2026-10-28 01:19 UTC.

## Correction to the preceding note

The prior note listed six settlement dates and omitted **2026-10-08**, when the Oct 5 13-week/26-week bill auctions and Oct 6 6-week bill auction settled. This replay corrects the event set to seven settlement dates:

| Date | Event class | Notes |
|---|---|---|
| Oct 8 | Treasury bill settlement | 13-week, 26-week and 6-week bills |
| Oct 13 | Treasury bill settlement | 17-week, 4-week and 8-week bills |
| Oct 15 | Coupon-security issuance settlement + bills | $119bn 3Y/10Y/30Y issuance settlement; bill settlements also occurred |
| Oct 20 | Treasury bill settlement | 17-week, 4-week and 8-week bills |
| Oct 22 | Treasury bill settlement | 13-week, 26-week and 6-week bills |
| Oct 23 | Coupon-security issuance settlement | $13bn 20Y reopening settlement |
| Oct 27 | Treasury bill settlement | 17-week, 4-week and 8-week bills |

**Critical distinction:** Oct 15 and Oct 23 are settlement dates for newly issued coupon securities. They are not Treasury coupon-payment dates to existing bondholders and not principal maturity dates. The current M1 event sample therefore tests settlement-day association, not the user's exact coupon/principal payout hypothesis.

## Method

- UTC calendar-day windows; event set above.
- Each full block required all expected M1 rows: 30/60/120/360 candles as appropriate.
- Path activity = sum of absolute consecutive M1 close-to-close changes, converted to pips (0.0001).
- Range = max high minus min low, converted to pips.
- Signed return = last close / first open minus 1, converted to pips.
- Control days = all other eligible dates in this short CSV window, not matched by weekday or volatility. They are not a rigorous control group.
- For 00–06 and later six-hour blocks, only complete 360-minute blocks were retained.

## A. Did anything unusual appear right from 00:00 UTC?

| Window from UTC day start | Event days | Controls | Median path, event | Median path, control | Ratio | Median range, event | Median range, control |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00–30 min | 7 | 14 | 16.6 | 14.2 | 1.17x | 4.6 | 4.7 |
| 00–60 min | 7 | 14 | 32.5 | 25.6 | 1.27x | 6.9 | 5.2 |
| 00–120 min | 7 | 13 | 65.8 | 50.7 | 1.30x | 14.4 | 5.4 |
| 00–360 min | 7 | 13 | 183.4 | 148.2 | 1.24x | 23.1 | 11.4 |

Interpretation:
- The first 30 minutes do **not** show a higher median high-low range (4.6 vs 4.7 pips), although path activity is modestly higher.
- By the first 60 minutes, median path activity is 27% higher and median range is 33% higher.
- Across the first two hours, median path activity is 30% higher and median range is 2.67 times the control median.
- The two-hour range comparison is especially sensitive to a very small sample and one or two large days. It must not be treated as a stable effect.

## B. What happens during later session blocks?

| UTC block | Event days | Controls | Median path, event | Median path, control | Ratio | Median range, event | Median range, control |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00–06 | 7 | 13 | 183.4 | 148.2 | 1.24x | 23.1 | 11.4 |
| 06–12 | 7 | 14 | 308.6 | 224.5 | 1.37x | 30.8 | 19.7 |
| 12–18 | 7 | 14 | 320.7 | 257.6 | 1.25x | 36.8 | 24.0 |
| 18–24 | 7 | 13 | 175.6 | 184.4 | 0.95x | 14.7 | 15.9 |

The largest median path-activity ratio appears in 06–12 UTC (1.37x). Activity is also elevated in the 00–06 block, so the difference is visible before the main European session in this sample. Evening activity is not elevated.

## C. Separate coupon-security issuance settlements from bill settlements

Only two dates in this history are coupon-security issuance settlements: Oct 15 and Oct 23. This is far too few for inference, but worth reporting separately.

For those two dates, versus all other eligible days:
- first 60-minute median path: 37.8 vs 27.3 pips (1.38x);
- first 120-minute median path: 76.4 vs 58.1 pips (1.32x);
- first 120-minute median range: 17.0 vs 8.0 pips.

This result is highly fragile (n=2) and still relates to settlement of new issuance, not existing-bond coupon payouts.

For the five bill-settlement dates:
- first 60-minute median path: 31.4 vs 27.3 pips (1.15x);
- first 120-minute median path: 65.3 vs 55.9 pips (1.17x).

These two categories should not be merged into one presumed mechanism.

## D. What this does and does not establish

**Supported as a preliminary descriptive observation:** on the seven selected issuance-settlement dates, the EUR/USD M1 path and range medians were higher than on other eligible dates in this narrow sample during 00–18 UTC. The difference was not evident in 18–24 UTC. The first 30 minutes alone did not show a higher median range.

**Not established:**
- that Treasury settlement caused the increased movement;
- that actual Treasury principal/coupon payout dates behave the same way;
- that direction is predictable;
- that the effect survives weekday/session matching, macro-news controls, a longer sample, or out-of-sample validation;
- that it can generate profitable 1-minute CALL/PUT entries after payout, spread and execution constraints.

## Next research work

1. Build the true U.S. principal-maturity and coupon-payment event panel from Treasury security-level records, not auction settlement dates.
2. Use the MSPD Table 3 Market security-level dataset. Its documented fields include CUSIP/security type, issue date, maturity date, interest rate, up to four interest-payment dates, and outstanding amount. This allows us to construct dated principal and coupon events from month-end snapshots; coupon cash amount must be calculated carefully by security type and outstanding principal, and bill maturity principal must be separated from coupon-bearing securities.
3. Reconcile predicted event cash flows with official Daily Treasury Statement / Schedules of Federal Debt by Day, and label what is observable versus estimated.
4. Obtain multiple years of EUR/USD M1 history (Dukascopy documents M1 availability back to 2003), preserving bid/ask/spread provenance.
5. Run weekday- and session-matched controls, volatility matching, event overlap tagging (CPI, payrolls, Fed/ECB, auctions), confidence intervals and day-cluster bootstrap.
6. Keep descriptive volatility study separate from direction/strategy tests.

## Primary-source data references

- Treasury's MSPD dataset metadata identifies the security-level Table 3 Market API resource: `https://www.transparency.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_3_market`.
- TreasuryDirect explains that MSPD lists securities, maturity dates and amounts outstanding.
- Treasury says Daily Treasury Statement summarizes cash and debt operations and is available by 4 p.m. the following business day.
- Dukascopy M1 EUR/USD historical data is documented from 2003 onward.

**Bottom line:** the corrected small-sample replay strengthens the reason to investigate early-day volatility on debt-settlement dates, but it still does not answer the exact question about coupon/principal payout days. The next decisive step is to build the actual payout calendar and expand the M1 sample.
