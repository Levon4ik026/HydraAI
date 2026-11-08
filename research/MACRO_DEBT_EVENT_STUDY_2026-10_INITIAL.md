# Macro debt-event study — EUR/USD, October 2026 (initial audit)

**Status:** preliminary descriptive audit; not a trading rule and not a completed intraday event study.  
**Research branch:** `hydra/research-validation`  
**Scope:** repository historical window recorded in the prior data audit: 2026-10-07 through 2026-10-28. That audit recorded 30,048 M1 rows, but the raw CSV could not be retrieved through the current GitHub file-content interface in this review. Therefore no M1 event-window returns, minute-of-day effects, or signal win rates are claimed here.

## 1. What counts as a debt/liquidity event

Keep separate:
1. announcement date — information becomes public;
2. auction date/time — price/yield and demand are discovered;
3. issue/settlement date — cash is exchanged for the new security;
4. maturity/coupon payment date — principal/interest is paid to holders;
5. Treasury cash-flow realization — deposits/withdrawals and TGA balance are recorded.

A settlement is not automatically a net liquidity drain of the full auction size: maturing principal may be refunded, SOMA add-ons/rollovers matter, and Treasury receipts/outlays also move the TGA. The Treasury Daily Treasury Statement is the primary daily source for operating cash, deposits/withdrawals and public-debt transactions.

## 2. US Treasury events in the available EUR/USD window

The official tentative auction schedule lists these dates (announcement / auction / settlement):

| Security | Announcement | Auction | Settlement |
|---|---:|---:|---:|
| 3-year note | Oct 1 | Oct 6 | Oct 15 |
| 10-year note reopening | Oct 1 | Oct 7 | Oct 15 |
| 30-year bond reopening | Oct 1 | Oct 8 | Oct 15 |
| 17-week bill | Oct 6 | Oct 7 | Oct 13 |
| 4-week and 8-week bills | Oct 6 | Oct 8 | Oct 13 |
| 6-week, 13-week and 26-week bills | Oct 8 | Oct 13 | Oct 15 |
| 17-week bill | Oct 13 | Oct 14 | Oct 20 |
| 4-week and 8-week bills | Oct 13 | Oct 15 | Oct 20 |
| 13-week and 26-week bills | Oct 15 | Oct 19 | Oct 22 |
| 6-week bill | Oct 15 | Oct 20 | Oct 22 |
| 20-year bond reopening | Oct 15 | Oct 21 | Oct 23 |
| 5-year TIPS reopening | Oct 15 | Oct 22 | Oct 30 (outside candle window) |
| 17-week bill | Oct 20 | Oct 21 | Oct 27 |
| 4-week and 8-week bills | Oct 20 | Oct 22 | Oct 27 |
| 13-week and 26-week bills | Oct 22 | Oct 26 | Oct 29 (outside candle window) |
| 6-week bill | Oct 22 | Oct 27 | Oct 29 (outside candle window) |

The October 6–8 coupon auctions totaled **$119bn gross**: $58bn 3-year, $39bn 10-year reopening and $22bn 30-year reopening. Reported auction results: 3-year yield 4.932%, bid-to-cover 2.62x (soft vs recent comparisons); 10-year yield 5.300%, bid-to-cover 2.77x (strong); 30-year yield 5.618%, bid-to-cover 2.54x (roughly average). The mixed demand profile is important: “large issuance” alone is not a sufficient event label; auction tails, bid-to-cover and bidder composition should be captured.

On Oct 21 the $13bn 20-year reopening cleared at 5.469%, bid-to-cover 2.73x. On Oct 27 a $70bn 5-year note auction cleared at 4.845%, bid-to-cover 2.33x (secondary auction-data source).

## 3. EU issuance events

The European Commission's 2026 calendar lists:
- EU-Bills auctions on Oct 7 and Oct 21;
- EU-Bonds auction on Oct 26, with non-competitive allocation the following day.

These are distinct from the national sovereign calendars (Germany, France, Italy, Spain, etc.). A complete euro-area event panel must add national debt-management offices and coupon/maturity cash flows; the EU calendar alone is not representative of all euro sovereign supply.

## 4. TGA cash-balance proxy and daily EUR/USD context

The following TGA values are closing balances in USD billions; daily changes are computed against the previous Treasury business-day observation. EUR/USD daily percentage changes are from a historical daily quote table, not from the Hydra M1 feed. This is a coarse screen only.

| Date | TGA close ($bn) | Change ($bn) | EUR/USD daily change | Context |
|---|---:|---:|---:|---|
| Oct 7 | 885.783 | +0.369 | -0.56% | $39bn 10Y auction; EU bills auction |
| Oct 8 | 887.469 | +1.686 | +0.13% | $22bn 30Y auction |
| Oct 13 | 920.214 | +47.688 | +0.39% | bill settlement cluster |
| Oct 14 | 885.823 | -34.391 | -0.38% | 17-week bill auction |
| Oct 15 | 934.690 | +48.867 | +0.56% | $119bn coupon-auction settlement; bill settlements |
| Oct 20 | 973.653 | +8.608 | +0.22% | 17-week / 4-week / 8-week bill settlement |
| Oct 21 | 945.153 | -28.500 | -0.04% | $13bn 20Y auction; EU bills auction |
| Oct 22 | 961.759 | +16.606 | -0.15% | bill settlement cluster |
| Oct 23 | 982.489 | +20.730 | -0.12% | 20Y settlement |
| Oct 26 | 1,020.700 | +38.211 | -0.26% | EU-Bonds auction |
| Oct 27 | 1,052.530 | +31.830 | -0.45% | 5Y Treasury auction; bill settlement |
| Oct 28 | 1,015.632 | -36.898 | +0.27% | TGA reversal after prior rise |

**Most important preliminary observation:** Oct 15 is a strong example of why a simplistic rule such as “Treasury settlement/TGA up = USD up” is not supported by this small sample. TGA rose by about $48.9bn on the day of the large coupon settlement, yet EUR/USD rose about 0.56% on the daily quote table (euro stronger). Oct 27 also had a TGA rise and EUR/USD fell, but Oct 28 reversed part of the TGA move while EUR/USD rebounded. Daily co-movement is mixed and cannot identify causality.

The TGA data source reports Oct 15 gross deposits of $449.18bn and withdrawals of $400.31bn, leaving the $48.87bn net increase. This confirms large gross Treasury cash flows that day, but does not prove the auction settlement was the sole cause. The official DTS describes daily cash/debt operations and reports deposits and withdrawals; the third-party table is used here as a discovery extract and must be reconciled to the official DTS before a final result.

## 5. What the price data says — and does not say

The daily EUR/USD record shows a broad decline across the period: the ECB reference series moved from 1.1177 on Oct 7 to 1.1133 on Oct 28, with a temporary recovery around Oct 15–16. Daily data also shows sizeable ranges on Oct 14–15. These facts establish that the window contains substantial FX movement, but do not establish that debt events caused it.

The most interesting candidate windows for minute-level replay are:
- **Oct 6–8:** sequential 3Y/10Y/30Y auctions, with contrasting auction-demand quality;
- **Oct 13–15:** concentrated bill settlements plus the $119bn coupon settlement and large TGA cash movements;
- **Oct 20–23:** 20Y auction and settlement, EU bill auction, and bill settlements;
- **Oct 26–28:** EU-Bond auction, US 5Y auction and large TGA moves.

## 6. Preliminary conclusions

1. There are multiple well-defined, timestampable debt events inside the available historical period. They are worth testing as potential context variables.
2. **No directional edge has been demonstrated.** The daily EUR/USD/TGA examples are mixed; one of the largest settlement/TGA-increase days coincided with EUR/USD rising.
3. The likely useful signal may be event-conditioned volatility/liquidity, not a deterministic CALL/PUT direction. This remains a hypothesis.
4. Auction quality (tail vs when-issued, bid-to-cover, indirect/direct/dealer shares), issue size, net new cash vs refunding, settlement date, TGA net/gross flows and central-bank context must be separate features.
5. Do not use the event date itself as a tradable signal until intraday timing is replayed and the effect survives matched non-event controls and out-of-sample validation.

## 7. Required next step for a proper result

Recover the raw EUR/USD M1 CSV into the research runtime (the repository's recorded history file is present by SHA but the current connector returned an empty content body). Then:
- verify timestamps, source, UTC alignment, gaps, weekends and quote provenance;
- use predeclared event windows (e.g. -120 to +240 minutes around auction result/settlement, with separate announcement and settlement windows);
- measure absolute return, range, realized volatility, directional return, spread/quote quality if available;
- compare each event window with matched same-weekday/same-hour non-event controls and a no-event baseline;
- distinguish scheduled cash/debt flows from surprise auction outcomes;
- test CALL/PUT/WAIT only after the market-reaction study, without tuning on the final holdout.

## Sources

- U.S. Treasury tentative auction schedule (official): https://home.treasury.gov/system/files/221/TentativeAuctionScheduleQ22026.pdf
- U.S. Treasury auction results and financing details: https://home.treasury.gov/policy-issues/financing-the-government/treasury-marketable-and-non-marketable-securities
- U.S. Treasury Quarterly Refunding / cash and borrowing statements: https://home.treasury.gov/news/press-releases/sb0590
- U.S. Treasury Daily Treasury Statement description: https://fiscal.treasury.gov/accounting/daily-treasury-statement
- European Commission EU-bill/EU-bond auction calendar: https://commission.europa.eu/strategy-and-policy/eu-budget/eu-borrower-investor-relations/auctions_en
- TGA historical daily extract (secondary presentation of Treasury cash data): https://500metrics.com/treasury/cash
- EUR/USD daily historical prices: https://ru.investing.com/currencies/eur-usd-historical-data and https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/eurofxref-graph-usd.fr.html
- October 2026 coupon-auction result cross-check: https://propdatalab.com/us-treasury-auction-calendar/
- October 2026 20-year auction result cross-check: https://www.cmegroup.com/education/events/econoday/692949

## Data limitations

- The TGA table is not the raw Treasury ledger; validate against official DTS before causal interpretation.
- Daily EUR/USD bars cannot establish reaction at 1:00 p.m. ET auction results or the settlement processing window.
- The repository's recorded 30,048-row M1 file could not be read through the current GitHub connector response; the prior audit metadata is not a substitute for re-reading the raw rows.
- The current sample covers only about three weeks. It is too short to estimate a stable event effect. Expand across multiple years and include event-free matched controls.
