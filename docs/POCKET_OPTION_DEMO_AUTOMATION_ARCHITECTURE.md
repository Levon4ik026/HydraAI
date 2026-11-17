# HydraAI — Pocket Option DEMO Automation Architecture

**Status:** architecture specification only. No order execution is enabled by this document.
**Target platform:** Pocket Option.
**Initial operating mode:** DEMO only.
**REAL mode:** hard-disabled by default; requires a separate explicit user authorization and a separately reviewed release.

## 1. Non-negotiable operating rules

1. The current application remains analysis-only until the DEMO execution adapter has been independently implemented and tested.
2. The first executable mode is DEMO. Startup must fail closed if the account mode cannot be positively identified as DEMO.
3. REAL mode must not be reachable through a UI toggle, config typo, environment variable, or automatic fallback. It requires a separate deliberate authorization flow and a distinct release/configuration review.
4. No OTC instruments. The initial symbol allowlist is EUR/USD only.
5. No trade is considered accepted until the platform confirms it. No result is considered settled until the platform's result/settlement state is observed and recorded.
6. If quote freshness, candle continuity, clock alignment, account mode, payout, connection state, or order status is uncertain, the system must abstain and record WAIT/BLOCKED.
7. Never use martingale, loss-chasing, or automatic stake escalation.

## 2. Runtime pipeline

`Feed -> DataQualityGate -> FeatureBuilder -> RegimeClassifier -> CandidateEvaluators -> StrategySelector -> RiskGate -> DemoExecutionAdapter -> Reconciliation -> Journal`

Each stage emits a timestamped, structured record. The execution adapter must not calculate indicators or select strategies; it receives a validated immutable order intent from the risk gate.

## 3. Market regime and strategy selection

The regime classifier labels the current completed-candle context using deterministic, testable features:

- trend: EMA structure/slope and directional persistence;
- volatility: ATR/range percentile and expansion/contraction;
- momentum: RSI and candle impulse;
- range/chop: efficiency ratio and directional overlap;
- data quality: freshness, gaps, duplicates, clock drift and sufficient lookback.

Regime labels are descriptive context, not a promise of edge. Every candidate independently evaluates its exact frozen entry rule and its predeclared market-situation eligibility. The selector may choose only among candidates whose entry and eligibility conditions are both satisfied. If none qualify, output WAIT. If multiple qualify, apply a deterministic priority/conflict policy; do not choose based on the most recent win or a small rolling sample.

Candidate entry definitions, expiry, and direction remain versioned and frozen during a forward test. Adaptation is limited to predeclared eligibility/allowlist decisions and risk controls. Any parameter change creates a new candidate version and requires a new out-of-sample evaluation.

## 4. Candidate registry integration

The five current DEMO shadow-watchlist candidates are:
- HYD-CAND-001
- HYD-CAND-008
- HYD-CAND-010
- HYD-CAND-012
- HYD-CAND-014

They remain research candidates, not proven profitable strategies. The registry's historical metrics use Dukascopy EUR/USD BID and an assumed 92% payout; they are not Pocket Option execution results. Forward DEMO performance must be calculated from observed platform entries, actual payout, and confirmed settlement.

Each signal record must include candidate ID/version, rule hash, market regime, situation eligibility, direction, expiry, signal candle timestamp, quote timestamp, requested/accepted order details, actual payout, settlement result, and reason for any rejection.

## 5. Risk gate

Before an order intent can reach the DEMO adapter, validate:
- account mode positively identified as DEMO;
- symbol is EUR/USD and not OTC;
- feed is FRESH and the required continuous M1 history is present;
- signal is based only on completed candles;
- quote timestamp and platform clock are within configured tolerance;
- actual payout meets a configured minimum;
- stake is fixed and within a configured DEMO limit;
- no duplicate order for the same candidate/signal;
- per-strategy and global concurrent-order limits;
- daily loss / drawdown stop and emergency stop;
- expiry is supported and matches the candidate version.

All thresholds must be explicit config values with safe defaults. A failed check blocks the order; there is no bypass path.

## 6. Execution adapter boundary

Implement the Pocket Option adapter only against an integration method that has been reviewed for platform compatibility and account-mode verification. Do not assume that reverse-engineered private WebSocket events or browser automation are stable or authorized. Keep any platform-specific transport isolated behind an interface:

- `identify_account_mode() -> DEMO | REAL | UNKNOWN`
- `get_quote(symbol) -> quote + timestamp + payout`
- `submit_demo_order(intent) -> accepted/rejected + platform_order_id`
- `get_order_status(platform_order_id)`
- `get_settlement(platform_order_id)`
- `close_or_cancel_if_supported(platform_order_id)`

If a supported and reliable order interface cannot be established, retain shadow mode and manual confirmation rather than silently automating through an unsupported protocol.

## 7. Reconciliation and learning

The journal is the source of truth for prospective evaluation. Reconcile every local order intent with platform acceptance and settlement. Record rejected, timed-out, duplicated, unknown, and manually intervened orders separately. Do not infer a win/loss from a later candle when platform settlement is unavailable.

Strategy health reports must include sample size, decisive WR, actual payout-adjusted net result, drawdown, loss streaks, skipped signals, execution failures, and uncertainty intervals. Do not promote or disable candidates solely from a handful of recent outcomes.

## 8. Delivery gates

### Gate A — source/data consistency
- Resolve the known mismatch: `hydra_market_analyzer.py` currently reads `observer_data/eurusd_candles.csv`, while the current guest collector writes `observer_data/eurusd_guest_candles.csv`.
- Audit every consumer, frozen executable path, and test fixture for the same canonical data path.
- Verify freshness/continuity checks against the actual collector output.

### Gate B — shadow selector
- Implement deterministic feature/regime output and the five frozen candidate evaluators.
- Run on live feed without submitting orders.
- Compare signals with an independently generated expected-event fixture.
- Confirm WAIT behavior on stale, gapped, duplicated, or insufficient data.

### Gate C — DEMO execution adapter
- Confirm a compatible, permitted integration and reliable DEMO account identification.
- Add idempotency, order-state polling, settlement reconciliation, rate limits, and emergency stop.
- Start with minimum fixed DEMO stake and one concurrent order globally.
- Run fault-injection tests before enabling live DEMO sessions.

### Gate D — forward DEMO validation
- Require a predeclared minimum sample and observation period.
- Compare accepted orders and settlements against Pocket Option history.
- Report actual payout per trade, slippage/latency, missing settlements, drawdown and net results.
- No automatic promotion to REAL.

### Gate E — separate REAL review
- Disabled by default and out of scope for the first release.
- Requires explicit user authorization, a separate configuration/release, renewed risk review, and a clear manual kill switch.

## 9. Immediate repository findings

- The research branch contains the candidate registry and research/audit modules, but the desktop UI entry point `main.py` was not present at the repository root on the inspected branch.
- `hydra_market_analyzer.py` reads the legacy `eurusd_candles.csv` path.
- `hydra_analyzer_loop.py` launches the analyzer/logger/AI sequence every 15 minutes; it is not an order-execution loop and must not be repurposed as one.
- This specification intentionally does not modify existing collector, analyzer, UI, or research candidate rules.

## 10. Acceptance criteria for first automated DEMO release

The DEMO executor is not ready until all of the following are true:
- account-mode detection returns DEMO and fails closed for UNKNOWN/REAL;
- no OTC instrument can pass validation;
- no stale/incomplete feed can create an order intent;
- duplicate intents cannot create duplicate platform orders;
- every accepted order has a platform ID and reconciled settlement;
- every rejected/unknown order is visible in the journal;
- emergency stop prevents new orders immediately;
- REAL mode remains inaccessible in the DEMO build;
- end-to-end tests pass against a safe test adapter before platform DEMO execution is enabled.
