# Treasury payment-calendar extraction: source validation and current blocker

**Status:** source/schema verified; historical security-level rows have not yet been ingested, so no actual coupon/principal event dates or cash amounts are claimed in this note.  
**Research branch:** `hydra/research-validation`

## 1. What is now verified

The U.S. Treasury MSPD Table 3 Market is the correct security-level source family for constructing a payment calendar. The catalog distribution points to the official Fiscal Data API resource `mspd_table_3_market`. The table is one row per marketable security/CUSIP per month-end record date and contains:
- record_date;
- security type / class;
- issue_date and maturity_date;
- interest_rate_pct;
- interest_pay_date_1 through interest_pay_date_4;
- issued_amt, inflation_adj_amt, redeemed_amt, outstanding_amt.

The independent dataset catalog describes monthly coverage from 2001 through 2026, about 152,500 rows, and states that amounts are in millions of USD. It also warns to exclude aggregate “Total Marketable” rows before summing.

## 2. Access test

Attempted to open:
1. official Fiscal Data dataset landing page;
2. official Treasury transparency API endpoint for Table 3 Market.

The current research environment returned HTTP 403 for the dataset landing page and an inaccessible-endpoint error for the API. The Data.gov catalog metadata remains visible and confirms the official API distribution. A third-party mirror (Subsets) documents the schema and offers a local download/query workflow, but its dataset rows were not retrievable through the current web connector.

**Important:** schema discovery is not data extraction. No event calendar, cash-flow total, or payout-day EUR/USD backtest has been produced from this source yet.

## 3. Calculation design once rows are available

- Build monthly security snapshots using only the latest record_date strictly before each event date (avoid look-ahead).
- Exclude aggregate total rows and securities with zero/negative outstanding balances.
- For each security, create principal event at maturity_date using the correct outstanding amount from the preceding snapshot.
- Create coupon events for each populated interest_pay_date field.
- For fixed-rate notes/bonds, a first-pass coupon estimate is outstanding principal × annual coupon rate / 2, with explicit exception handling for odd first/last coupons, reopenings, partial redemptions and inflation-adjusted TIPS principal.
- Do not apply the fixed-rate formula blindly to bills or FRNs. Bills have no coupon; FRNs reset; TIPS coupon base is inflation-adjusted principal.
- Keep gross principal maturities, coupon payments, bill redemptions, and new-issue settlements as separate event classes.
- Reconcile totals and dates against official Daily Treasury Statement / schedules before using the event panel in statistical tests.

## 4. EUR/USD M1 acquisition route verified

Dukascopy's current documentation confirms:
- EUR/USD instrument id `eurusd`;
- M1 candles supported;
- bid and ask price sides available separately;
- UTC timestamps;
- CSV output;
- historical date-range download via `dukascopy-node`.

The docs specify one request per day for M1 candles. This gives us a practical path to multi-year data acquisition. However, no multi-year file has yet been downloaded into this repository, and the current 30,048-row CSV remains the only M1 sample used in the settlement-day replay.

## 5. Current research conclusion

The previous October 2026 replay concerns **new-issue settlement dates**, not actual coupon payments or principal maturities to existing holders. Its apparent pooled volatility uplift was not robust to the limited weekday-only diagnostic comparison. Therefore it is not evidence of a payout-day effect.

**Next gate:** ingest the Treasury Table 3 Market rows and several years of EUR/USD M1 BID/ASK candles, then construct actual payment dates/amounts and run weekday/session/volatility/news-matched event studies. Until then, no payout-day volatility edge or CALL/PUT signal is established.

## Sources

- Official Data.gov MSPD catalog and distribution metadata: https://catalog.data.gov/dataset/monthly-statement-of-the-public-debt-mspd
- Official Fiscal Data MSPD dataset page: https://fiscaldata.treasury.gov/datasets/monthly-statement-public-debt/
- Treasury Table 3 Market API resource: https://www.transparency.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_3_market
- Table 3 Market schema and coverage mirror (secondary discovery source): https://subsets.io/datasets/us-treasury-fiscal-data-v1-debt-mspd-mspd-table-3-market
- Dukascopy historical M1 download quick start: https://www.dukascopy-node.app/quick-start
- Dukascopy API configuration (price side, timestamps, timeframe): https://www.dukascopy-node.app/config/node
