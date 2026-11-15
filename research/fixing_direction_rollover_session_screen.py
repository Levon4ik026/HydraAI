#!/usr/bin/env python3
"""Direct post-fixing CALL and rollover-excluded NY session reversal screen."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from fixing_daily_reversal_screen import (
    PAYOUT, PAYOUT_GRID, BOOTSTRAP_REPS, BOOTSTRAP_SEED,
    UTC, NY, TOKYO, BERLIN, LONDON,
    load_m1, minute_window, period_quality, local_time,
    stats, day_cluster_bootstrap, split_records, fmt_pct, fmt_units,
)

HORIZONS = (5, 10, 15, 20, 30, 60)
BREAKEVEN_WR = 100 * (1 / (1 + PAYOUT))


def outcome(entry, settle, side):
    delta = settle.close - entry.open
    if abs(delta) <= 1e-12:
        return "D"
    won = delta > 0 if side == "CALL" else delta < 0
    return "W" if won else "L"


def make_trade(cid, signal_time, entry_time, by_ts, side, pre_return, label, expiry):
    window = minute_window(by_ts, entry_time, expiry)
    if window is None:
        return None
    entry, settle = window[0], window[-1]
    control_side = "PUT" if side == "CALL" else "CALL"
    return {
        "candidate_id": cid, "signal_time": signal_time, "entry_time": entry_time,
        "settle_time": entry_time + timedelta(minutes=expiry),
        "expiry_minutes": expiry, "side": side, "control_side": control_side,
        "outcome": outcome(entry, settle, side),
        "control_outcome": outcome(entry, settle, control_side),
        "entry_price": entry.open, "exit_price": settle.close,
        "pre_move_log_return": pre_return, "event_label": label,
    }


def fixing_events(bars, by_ts):
    specs = (
        ("FXFIX-TOKYO-PREFIX-USD-REV-CALL", "Tokyo", TOKYO, 9, 55, "TOKYO_NY17"),
        ("FXFIX-ECB-PREFIX-USD-REV-CALL", "ECB Frankfurt", BERLIN, 14, 15, "EUROPE_OPEN"),
        ("FXFIX-LONDON-PREFIX-USD-REV-CALL", "London", LONDON, 16, 0, "EUROPE_OPEN"),
    )
    first_day = bars[0].ts.date() - timedelta(days=3)
    last_day = bars[-1].ts.date() + timedelta(days=3)
    out = {}
    for cid, label, zone, hh, mm, window_kind in specs:
        events, eligible, excluded, raw_signals = [], 0, 0, 0
        d = first_day
        while d <= last_day:
            if d.weekday() < 5:
                fix = local_time(d, hh, mm, zone)
                if window_kind == "TOKYO_NY17":
                    ny_date = fix.astimezone(NY).date()
                    start = local_time(ny_date, 17, 0, NY)
                else:
                    start = local_time(d, 7, 0, zone)
                pre_minutes = int((fix - start).total_seconds() // 60)
                pre = minute_window(by_ts, start, pre_minutes)
                future = minute_window(by_ts, fix, 60)
                if pre is None or future is None:
                    excluded += 1
                else:
                    eligible += 1
                    move = math.log(pre[-1].close / pre[0].open)
                    # Literature-directed signal: USD strengthened before fix, so EUR/USD fell.
                    if move < -1e-12:
                        raw_signals += 1
                        events.append({
                            "signal_time": fix, "entry_time": fix, "side": "CALL",
                            "pre_return": move, "label": label,
                        })
            d += timedelta(days=1)
        if window_kind == "TOKYO_NY17":
            rule = "Pre-window from 17:00 America/New_York on the NY local date of the Tokyo fixing to 09:55 Asia/Tokyo; if completed EUR/USD log return < 0, CALL at fixing-time M1 open; otherwise WAIT."
        else:
            rule = f"Pre-window from 07:00 to {hh:02d}:{mm:02d} {zone.key}; if completed EUR/USD log return < 0, CALL at fixing-time M1 open; otherwise WAIT."
        out[cid] = {
            "label": label, "events": events, "eligible_windows": eligible,
            "excluded_windows": excluded, "raw_signal_events": raw_signals,
            "rule": rule, "market_regime": "USD-strength pre-fix / post-fix reversal",
        }
    return out


def ny_session_events(bars, by_ts):
    out = {}
    first_day = bars[0].ts.date() - timedelta(days=40)
    last_day = bars[-1].ts.date() + timedelta(days=12)

    # Daily 23-hour NY session excludes the 17:00–18:00 rollover break.
    daily = []
    quality_rejects = 0
    d = first_day
    while d <= last_day:
        if d.weekday() in (6, 0, 1, 2, 3):
            start = local_time(d, 18, 0, NY)
            end = local_time(d + timedelta(days=1), 17, 0, NY)
            q = period_quality(by_ts, start, end, min_coverage=0.99, max_gap=5)
            if q:
                daily.append({"start": start, "end": end, **q})
            else:
                quality_rejects += 1
        d += timedelta(days=1)

    cid = "NY18-DAILY-SHOCK-FADE"
    events, eligible, excluded, raw_signals = [], 0, 0, 0
    for i in range(20, len(daily)):
        cur, prior = daily[i], daily[i-20:i]
        next_start = cur["end"] + timedelta(hours=1)
        if minute_window(by_ts, next_start, 60) is None:
            excluded += 1
            continue
        eligible += 1
        threshold = sum(abs(x["log_return"]) for x in prior) / len(prior)
        if abs(cur["log_return"]) + 1e-15 < threshold:
            continue
        raw_signals += 1
        side = "PUT" if cur["log_return"] > 0 else "CALL"
        events.append({
            "signal_time": cur["end"], "entry_time": next_start, "side": side,
            "pre_return": cur["log_return"], "label": "NY 18:00–17:00 completed daily session",
        })
    out[cid] = {
        "label": "NY rollover-excluded daily shock fade", "events": events,
        "eligible_windows": eligible, "excluded_windows": excluded + quality_rejects,
        "quality_rejected_sessions": quality_rejects, "raw_signal_events": raw_signals,
        "rule": "Completed 18:00–17:00 New York session absolute log return >=1.0x mean absolute return of preceding 20 valid sessions (current excluded); fade at next 18:00 NY open.",
        "market_regime": "large completed rollover-excluded NY daily session move",
    }

    # Weekly session permits the known daily 17:00–18:00 NY closure but excludes the weekend.
    weekly = []
    weekly_quality_rejects = 0
    d = first_day
    while d <= last_day:
        if d.weekday() == 6:
            start = local_time(d, 18, 0, NY)
            end = local_time(d + timedelta(days=5), 17, 0, NY)
            q = period_quality(by_ts, start, end, min_coverage=0.95, max_gap=65)
            if q:
                weekly.append({"start": start, "end": end, **q})
            else:
                weekly_quality_rejects += 1
        d += timedelta(days=1)

    cid = "NY18-WEEKLY-SHOCK-FADE"
    events, eligible, excluded, raw_signals = [], 0, 0, 0
    for i in range(13, len(weekly)):
        cur, prior = weekly[i], weekly[i-13:i]
        next_start = cur["start"] + timedelta(days=7)
        if minute_window(by_ts, next_start, 60) is None:
            excluded += 1
            continue
        eligible += 1
        threshold = 0.75 * sum(abs(x["log_return"]) for x in prior) / len(prior)
        if abs(cur["log_return"]) + 1e-15 < threshold:
            continue
        raw_signals += 1
        side = "PUT" if cur["log_return"] > 0 else "CALL"
        events.append({
            "signal_time": cur["end"], "entry_time": next_start, "side": side,
            "pre_return": cur["log_return"], "label": "NY Sunday 18:00–Friday 17:00 completed week",
        })
    out[cid] = {
        "label": "NY rollover-excluded weekly shock fade", "events": events,
        "eligible_windows": eligible, "excluded_windows": excluded + weekly_quality_rejects,
        "quality_rejected_sessions": weekly_quality_rejects, "raw_signal_events": raw_signals,
        "rule": "Completed Sunday 18:00–Friday 17:00 New York week absolute log return >=0.75x mean absolute return of preceding 13 valid weeks (current excluded); fade at next Sunday 18:00 NY open.",
        "market_regime": "large completed rollover-excluded NY trading-week move",
    }
    return out


def records_for_expiry(cid, info, by_ts, expiry):
    rows = []
    for e in info["events"]:
        r = make_trade(cid, e["signal_time"], e["entry_time"], by_ts, e["side"],
                       e["pre_return"], e["label"], expiry)
        if r:
            rows.append(r)
    return sorted(rows, key=lambda x: x["entry_time"])


def choose_expiry(info, by_ts, d1, d2):
    grid = []
    candidates = []
    for expiry in HORIZONS:
        rows = records_for_expiry(info["candidate_id"], info, by_ts, expiry)
        splits, purged = split_records(rows, d1, d2)
        s = stats(splits["TRAIN"])
        lower = s["wilson_95_pct"][0] if s["wilson_95_pct"] else None
        eligible = (
            s["n"] >= 30 and s["net_units"] > 0 and s["wr_pct"] is not None
            and s["wr_pct"] > BREAKEVEN_WR
        )
        grid.append({
            "expiry_minutes": expiry, "train": s, "train_purged": purged["TRAIN"],
            "selection_eligible": eligible,
        })
        if eligible:
            candidates.append((lower, s["net_units"], -expiry, expiry))
    selected = max(candidates)[3] if candidates else None
    return selected, grid


def build_report(candidates, data_meta, protocol_path, script_path, out_dir):
    first = __import__("datetime").datetime.fromisoformat(data_meta["first_utc"])
    last = __import__("datetime").datetime.fromisoformat(data_meta["last_utc"])
    span_days = (last.date() - first.date()).days
    d1 = first.date() + timedelta(days=int(span_days * 0.60))
    d2 = first.date() + timedelta(days=int(span_days * 0.80))
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# EUR/USD direct fixing and rollover-excluded session discovery", "",
        f"- Captured UTC: {__import__('datetime').datetime.now(UTC).isoformat()}",
        "- Branch: hydra/research-validation",
        f"- Source: Dukascopy EUR/USD M1 BID; coverage {data_meta['first_utc']} — {data_meta['last_utc']}",
        f"- Raw M1 rows: {data_meta['raw_rows']:,}; valid unique: {data_meta['valid_unique_rows']:,}; invalid: {data_meta['invalid_rows']:,}; duplicate timestamps: {data_meta['duplicate_timestamp_rows']:,}",
        f"- Gaps: {data_meta['gap_intervals']:,} intervals; {data_meta['missing_m1_minutes']:,} missing minutes; largest missing interval {data_meta['largest_missing_interval_minutes']:,} minutes; continuity segments {data_meta['continuity_segments']:,}",
        f"- Raw CSV SHA-256: {data_meta['raw_csv_sha256']}",
        f"- Script SHA-256: {hashlib.sha256(script_path.read_bytes()).hexdigest()}",
        f"- Protocol SHA-256: {hashlib.sha256(protocol_path.read_bytes()).hexdigest()}",
        f"- Calendar split: TRAIN before {d1}; VALIDATION {d1}–{d2 - timedelta(days=1)}; TEST from {d2}",
        "- Historical TEST is from a source period previously inspected by other HydraAI screens; it is exploratory, not pristine independent confirmation.",
        "- Expiry selection uses TRAIN only: N>=30, positive net at 92%, decisive WR above 52.0833%; maximize Wilson 95% lower bound, then net, then shorter expiry.",
        "- All entries use exact M1 opens; expiry settles at the close of the final included M1 bar. Missing outcome minutes exclude the trade.",
        "- Payout accounting: WIN +0.92u, LOSS -1u, DRAW 0u. Matched control is the opposite direction at the same timestamps.",
        "- Dukascopy BID is not Pocket Option executable pricing; spread, quote construction, platform payout, latency and settlement are not modeled.", "",
        "## Candidate results", "",
        "| Candidate | Selected expiry | N | W/L/D | WR | Net @92% | Max DD | VALIDATION N/WR/net | TEST N/WR/net | Status |",
        "|---|---:|---:|---|---:|---:|---:|---|---|---|",
    ]
    all_selected_trades = []
    result_manifest = []
    for cid, info in candidates.items():
        info["candidate_id"] = cid
        selected, grid = choose_expiry(info, candidates["_by_ts"], d1, d2)
        if selected is None:
            status = "NO_TRAIN_VARIANT_PASS"
            overall = stats([])
            control = stats([], "control_outcome")
            splits = {"TRAIN": stats([]), "VALIDATION": stats([]), "TEST": stats([])}
            purged = {"TRAIN": 0, "VALIDATION": 0}
            rows = []
            bootstrap = day_cluster_bootstrap([])
            side_stats = {"CALL": stats([]), "PUT": stats([])}
        else:
            rows = records_for_expiry(cid, info, candidates["_by_ts"], selected)
            all_selected_trades.extend(rows)
            overall = stats(rows)
            control = stats(rows, "control_outcome")
            split_rows, purged = split_records(rows, d1, d2)
            splits = {k: stats(v) for k, v in split_rows.items()}
            bootstrap = day_cluster_bootstrap(rows)
            side_stats = {side: stats([r for r in rows if r["side"] == side]) for side in ("CALL", "PUT")}
            val, test = splits["VALIDATION"], splits["TEST"]
            if val["n"] < 30 or test["n"] < 30:
                status = "INSUFFICIENT_SAMPLE"
            elif (val["net_units"] > 0 and test["net_units"] > 0
                  and val["wr_pct"] is not None and test["wr_pct"] is not None
                  and val["wr_pct"] > BREAKEVEN_WR and test["wr_pct"] > BREAKEVEN_WR):
                status = "PRELIMINARY_LEAD"
            else:
                status = "NOT_PASS_PRIMARY_SCREEN"
        val, test = splits["VALIDATION"], splits["TEST"]
        val_txt = f"{val['n']}/{fmt_pct(val['wr_pct'])}/{fmt_units(val['net_units'])}"
        test_txt = f"{test['n']}/{fmt_pct(test['wr_pct'])}/{fmt_units(test['net_units'])}"
        lines.append(
            f"| {cid} | {selected if selected is not None else 'none'} | {overall['n']} | "
            f"{overall['w']}/{overall['l']}/{overall['d']} | {fmt_pct(overall['wr_pct'])} | "
            f"{fmt_units(overall['net_units'])} | {overall['max_drawdown_units']:.2f}u | "
            f"{val_txt} | {test_txt} | {status} |"
        )
        lines += [
            "", f"### {cid} — {info['label']}", "",
            f"- Exact rule: {info['rule']}",
            f"- Market regime: {info['market_regime']}",
            f"- Eligible windows: {info['eligible_windows']:,}; raw triggers: {info['raw_signal_events']:,}; excluded/quality-rejected windows: {info['excluded_windows']:,}.",
            f"- Signal share: {(100*info['raw_signal_events']/info['eligible_windows'] if info['eligible_windows'] else 0):.3f}%; WAIT share: {(100*(1-info['raw_signal_events']/info['eligible_windows']) if info['eligible_windows'] else 100):.3f}%.",
            f"- TRAIN expiry selection: {selected if selected is not None else 'no eligible expiry'} using Wilson lower bound; no VALIDATION/TEST metric was used for selection.", "",
            "| Expiry | TRAIN N | W/L/D | WR | Net @92% | Wilson lower | Eligible for selection |",
            "|---:|---:|---|---:|---:|---:|---|",
        ]
        for g in grid:
            s = g["train"]
            lower = s["wilson_95_pct"][0] if s["wilson_95_pct"] else None
            lines.append(
                f"| {g['expiry_minutes']}m | {s['n']} | {s['w']}/{s['l']}/{s['d']} | "
                f"{fmt_pct(s['wr_pct'])} | {fmt_units(s['net_units'])} | "
                f"{fmt_pct(lower)} | {'yes' if g['selection_eligible'] else 'no'} |"
            )
        lines += [
            "", f"- Selected-expiry overall: N={overall['n']}, W/L/D={overall['w']}/{overall['l']}/{overall['d']}, WR={fmt_pct(overall['wr_pct'])}, Wilson 95%={overall['wilson_95_pct']}, net={fmt_units(overall['net_units'])}, ROI={fmt_pct(overall['roi_pct'])}, expectancy={fmt_units(overall['expectancy_units'])}/trade, PF={overall['profit_factor']}, max DD={overall['max_drawdown_units']:.2f}u, longest losing streak={overall['longest_losing_streak']}.",
            f"- Matched opposite-direction control: N={control['n']}, W/L/D={control['w']}/{control['l']}/{control['d']}, WR={fmt_pct(control['wr_pct'])}, net={fmt_units(control['net_units'])}.",
            f"- Candidate side split: CALL N={side_stats['CALL']['n']} WR={fmt_pct(side_stats['CALL']['wr_pct'])} net={fmt_units(side_stats['CALL']['net_units'])}; PUT N={side_stats['PUT']['n']} WR={fmt_pct(side_stats['PUT']['wr_pct'])} net={fmt_units(side_stats['PUT']['net_units'])}.",
            f"- Day-cluster bootstrap ({BOOTSTRAP_REPS:,} reps, seed {BOOTSTRAP_SEED}): {bootstrap}.",
            f"- Split purges: TRAIN={purged['TRAIN']}, VALIDATION={purged['VALIDATION']}.", "",
            "| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |",
            "|---|---:|---|---:|---|---:|---:|---:|---:|---:|",
        ]
        for split_name in ("TRAIN", "VALIDATION", "TEST"):
            s = splits[split_name]
            lines.append(
                f"| {split_name} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {fmt_pct(s['wr_pct'])} | "
                f"{s['wilson_95_pct']} | {fmt_units(s['net_units'])} | {fmt_pct(s['roi_pct'])} | "
                f"{s['profit_factor']} | {s['max_drawdown_units']:.2f}u | {s['longest_losing_streak']} |"
            )
        lines += ["", "| Payout | Net units |", "|---:|---:|"]
        for payout in PAYOUT_GRID:
            lines.append(f"| {payout:.0%} | {stats(rows, payout=payout)['net_units']:+.2f} |")
        months = defaultdict(list)
        for r in rows:
            months[r["signal_time"].strftime("%Y-%m")].append(r)
        lines += ["", "| UTC month | N | W/L/D | WR | Net @92% |", "|---|---:|---|---:|---:|"]
        for month in sorted(months):
            s = stats(months[month])
            lines.append(f"| {month} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {fmt_pct(s['wr_pct'])} | {s['net_units']:+.2f}u |")
        result_manifest.append({
            "candidate_id": cid, "rule": info["rule"], "market_regime": info["market_regime"],
            "eligible_windows": info["eligible_windows"], "raw_signal_events": info["raw_signal_events"],
            "excluded_windows": info["excluded_windows"], "quality_rejected_sessions": info.get("quality_rejected_sessions", 0),
            "selected_expiry_minutes": selected, "train_expiry_grid": grid,
            "overall": overall, "matched_control": control, "side_stats": side_stats,
            "splits": splits, "purged": purged, "bootstrap": bootstrap, "status": status,
        })
    fields = ["candidate_id", "signal_time", "entry_time", "settle_time", "expiry_minutes",
              "side", "control_side", "outcome", "control_outcome", "entry_price", "exit_price",
              "pre_move_log_return", "event_label"]
    with (out_dir / "trades.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in sorted(all_selected_trades, key=lambda x: (x["candidate_id"], x["entry_time"])):
            writer.writerow({k: (r[k].isoformat() if hasattr(r[k], "isoformat") else r[k]) for k in fields})
    passed = [x["candidate_id"] for x in result_manifest if x["status"] == "PRELIMINARY_LEAD"]
    lines += [
        "", "## Primary screening outcome", "",
        f"- Preliminary leads passing the fixed screen: {len(passed)}/5 — {', '.join(passed) if passed else 'none'}.",
        "- Passing is preliminary only. Historical TEST is from a previously inspected source period; prospective validation and Pocket Option DEMO quote/settlement comparison remain mandatory.",
        "- Do not fill a five-candidate batch with under-sampled or negative rows.", "",
        "## Interpretation limits", "",
        "- Expiry selection is TRAIN-only. The selected VALIDATION/TEST rows are not used to choose expiry.",
        "- Wilson intervals assume independent outcomes; day-cluster bootstrap preserves within-day clustering but not all multi-day dependence.",
        "- The five families are not pooled. Matched controls use identical timestamps and opposite direction.",
        "- BID-only historical results do not establish Pocket Option executable profitability.", "",
        "## Reproducibility", "", "- Machine-readable manifest: manifest.json", "- Selected trade ledger: trades.csv", "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "captured_at_utc": __import__("datetime").datetime.now(UTC).isoformat(),
        "branch": "hydra/research-validation",
        "protocol": "research-artifacts/fixing-direction-rollover-session-protocol-v1.md",
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        "data": data_meta,
        "split_boundaries": {"train_end_exclusive": d1.isoformat(), "validation_end_exclusive": d2.isoformat()},
        "expiry_grid_minutes": HORIZONS, "selection_metric": "max TRAIN Wilson lower bound subject to TRAIN N>=30, net>0, decisive WR>break-even",
        "payout": PAYOUT, "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_seed": BOOTSTRAP_SEED,
        "candidate_results": result_manifest, "preliminary_leads": passed, "batch_ready": len(passed) >= 5,
        "execution_caveat": "Dukascopy EUR/USD BID is not Pocket Option executable pricing.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    bars, by_ts, meta = load_m1(args.data)
    candidates = {}
    candidates.update(fixing_events(bars, by_ts))
    candidates.update(ny_session_events(bars, by_ts))
    candidates["_by_ts"] = by_ts
    manifest = build_report(candidates, meta, args.protocol, Path(__file__), args.out_dir)
    print(
        f"Direct fixing/session screen complete: valid M1={meta['valid_unique_rows']:,}; "
        f"candidates={len(manifest['candidate_results'])}; preliminary leads={len(manifest['preliminary_leads'])}; "
        f"report={args.out_dir / 'report.md'}"
    )


if __name__ == "__main__":
    main()
