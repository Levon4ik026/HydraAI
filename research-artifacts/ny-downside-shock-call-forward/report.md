# NY downside-shock CALL — locked forward audit

Source: Dukascopy EURUSD M1 BID; valid unique rows=1,030,522; invalid or pre-2024 rows excluded=38,478.
Coverage: 2024-01-01T22:00:00+00:00 — 2026-11-15T23:58:00+00:00.
Valid NY sessions=578; raw shock matches=117.
Frozen cutoff=2026-11-13T21:59:00+00:00 exclusive; only later entries scored.
Frozen rule: 18:00–16:59 America/New_York completed session; >=99% minute coverage; no gap >5m; after 20 preceding valid sessions, current log return <= -1.0x their mean absolute return; CALL at next 18:00 NY open only.
Expiry fixed 30m: entry M1 open, settlement close of entry+29m. All 30 bars required. No PUT signals.
Payout +0.92/-1/0; break-even decisive WR=52.0833%. Matched PUT comparator is secondary only.
Dukascopy BID is not Pocket Option executable pricing; spread, platform quotes, payout variation and latency are not modeled.

## Primary CALL results

| Trades | W/L/D | Decisive WR | Net | ROI/trade | PF | Max DD | Max loss streak | Active days | Daily bootstrap 95% CI | P(net>0) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0/0/0 | n/a | +0.00u | n/a | 0.000 | 0.00u | 0 | 0 | [+0.00, +0.00]u | 0.0% |

## Matched PUT comparator

Trades=0; W/L/D=0/0/0; WR=n/a; net=+0.00u; PF=0.000.

## Decision

- Fewer than 100 forward CALL trades; minimum statistical review threshold=100.
- Under 100 trades is insufficient; no parameter, direction, expiry, session or filter may be changed during monitoring.
- Monitoring only. No production approval, real trades, OTC or automatic execution.
