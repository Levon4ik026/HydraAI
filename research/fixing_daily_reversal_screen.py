#!/usr/bin/env python3
"""Pre-registered EURUSD M1 fixing/session reversal screen. Research only."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PAYOUT = 0.92
EXPIRY_MINUTES = 60
BOOTSTRAP_REPS = 2000
BOOTSTRAP_SEED = 20261115
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")
BERLIN = ZoneInfo("Europe/Berlin")
LONDON = ZoneInfo("Europe/London")
PAYOUT_GRID = (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.95, 1.00)


@dataclass(frozen=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float


def parse_timestamp(row, fields):
    if "timestamp" in fields:
        value = int(float(row["timestamp"]))
        scale = 1000.0 if abs(value) > 10_000_000_000 else 1.0
        ts = datetime.fromtimestamp(value / scale, tz=UTC)
    else:
        key = "datetime_utc" if "datetime_utc" in fields else "datetime"
        raw = row[key].strip()
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        ts = ts.astimezone(UTC)
    if ts.second != 0 or ts.microsecond != 0:
        raise ValueError("timestamp is not aligned to a whole minute")
    return ts


def load_m1(path):
    raw_bytes = path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    parsed = {}
    raw_rows = invalid_rows = duplicate_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        required = {"open", "high", "low", "close"}
        if not required.issubset(fields) or not ({"timestamp", "datetime_utc", "datetime"} & set(fields)):
            raise ValueError(f"Unexpected M1 CSV header: {fields}")
        for row in reader:
            raw_rows += 1
            try:
                ts = parse_timestamp(row, fields)
                o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
                if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                    raise ValueError("non-finite or non-positive OHLC")
                if h < max(o, l, c) or l > min(o, c):
                    raise ValueError("invalid OHLC envelope")
                if ts in parsed:
                    duplicate_rows += 1
                parsed[ts] = Bar(ts, o, h, l, c)
            except Exception:
                invalid_rows += 1
    bars = [parsed[t] for t in sorted(parsed)]
    if len(bars) < 100_000:
        raise SystemExit(f"Insufficient history: only {len(bars):,} valid unique M1 rows")
    gaps = []
    for left, right in zip(bars, bars[1:]):
        missing = int((right.ts - left.ts).total_seconds() // 60) - 1
        if missing > 0:
            gaps.append(missing)
    meta = {
        "raw_rows": raw_rows, "valid_unique_rows": len(bars),
        "invalid_rows": invalid_rows, "duplicate_timestamp_rows": duplicate_rows,
        "first_utc": bars[0].ts.isoformat(), "last_utc": bars[-1].ts.isoformat(),
        "gap_intervals": len(gaps), "missing_m1_minutes": sum(gaps),
        "largest_missing_interval_minutes": max(gaps, default=0),
        "continuity_segments": 1 + len(gaps), "raw_csv_sha256": digest,
    }
    return bars, {b.ts: b for b in bars}, meta


def minute_window(by_ts, start, minutes):
    """Exact contiguous M1 window [start, start+minutes)."""
    out = []
    for i in range(minutes):
        b = by_ts.get(start + timedelta(minutes=i))
        if b is None:
            return None
        out.append(b)
    return out


def outcome(entry, settle, side):
    delta = settle.close - entry.open
    if abs(delta) <= 1e-12:
        return "D"
    won = delta > 0 if side == "CALL" else delta < 0
    return "W" if won else "L"


def make_trade(cid, signal_time, entry_time, by_ts, side, pre_return, label):
    window = minute_window(by_ts, entry_time, EXPIRY_MINUTES)
    if window is None:
        return None
    entry, settle = window[0], window[-1]
    control_side = "PUT" if side == "CALL" else "CALL"
    return {
        "candidate_id": cid, "signal_time": signal_time, "entry_time": entry_time,
        "settle_time": entry_time + timedelta(minutes=EXPIRY_MINUTES),
        "side": side, "control_side": control_side,
        "outcome": outcome(entry, settle, side),
        "control_outcome": outcome(entry, settle, control_side),
        "entry_price": entry.open, "exit_price": settle.close,
        "pre_move_log_return": pre_return, "event_label": label,
    }


def local_time(d, hh, mm, zone):
    return datetime.combine(d, time(hh, mm), tzinfo=zone).astimezone(UTC)


def fixing_candidates(bars, by_ts):
    specs = (
        ("FXFIX-TOKYO-FADE-60", "Tokyo", TOKYO, 9, 55, None, 240),
        ("FXFIX-ECB-FADE-60", "ECB Frankfurt", BERLIN, 14, 15, (7, 0), None),
        ("FXFIX-LONDON-FADE-60", "London", LONDON, 16, 0, (7, 0), None),
    )
    first_day = bars[0].ts.date() - timedelta(days=2)
    last_day = bars[-1].ts.date() + timedelta(days=2)
    output = {}
    for cid, label, zone, hh, mm, start_clock, lookback in specs:
        records, eligible, excluded, raw_signals = [], 0, 0, 0
        d = first_day
        while d <= last_day:
            if d.weekday() < 5:
                fix = local_time(d, hh, mm, zone)
                start = fix - timedelta(minutes=lookback) if start_clock is None else local_time(d, start_clock[0], start_clock[1], zone)
                pre_minutes = int((fix - start).total_seconds() // 60)
                pre = minute_window(by_ts, start, pre_minutes)
                post = minute_window(by_ts, fix, EXPIRY_MINUTES)
                if pre is None or post is None:
                    excluded += 1
                else:
                    eligible += 1
                    move = math.log(pre[-1].close / pre[0].open)
                    if abs(move) > 1e-12:
                        raw_signals += 1
                        side = "PUT" if move > 0 else "CALL"
                        trade = make_trade(cid, fix, fix, by_ts, side, move, label)
                        if trade:
                            records.append(trade)
                        else:
                            excluded += 1
            d += timedelta(days=1)
        rule = (
            f"Fade the completed EUR/USD return over {lookback} minutes before {hh:02d}:{mm:02d} {zone.key} fixing; enter at fixing-time M1 open; 60-minute expiry."
            if start_clock is None else
            f"Fade the completed EUR/USD return from {start_clock[0]:02d}:{start_clock[1]:02d} to {hh:02d}:{mm:02d} {zone.key}; enter at fixing-time M1 open; 60-minute expiry."
        )
        output[cid] = {
            "label": label, "records": records, "eligible_windows": eligible,
            "excluded_windows": excluded, "raw_signal_events": raw_signals,
            "rule": rule, "expiry_minutes": EXPIRY_MINUTES,
            "market_regime": "fixing-time pre-move / post-fixing reversal",
        }
    return output


def period_quality(by_ts, start, end, min_coverage=0.99, max_gap=5):
    """Validate [start,end); permits only small feed holes, never weekend bridging."""
    expected = int((end - start).total_seconds() // 60)
    if expected <= 0 or start not in by_ts or end - timedelta(minutes=1) not in by_ts:
        return None
    present = []
    t = start
    while t < end:
        if t in by_ts:
            present.append(t)
        t += timedelta(minutes=1)
    if len(present) < math.ceil(expected * min_coverage):
        return None
    largest_gap = max((int((b - a).total_seconds() // 60) - 1 for a, b in zip(present, present[1:])), default=0)
    if largest_gap > max_gap:
        return None
    first, last = by_ts[start], by_ts[end - timedelta(minutes=1)]
    return {
        "open": first.open, "close": last.close,
        "log_return": math.log(last.close / first.open),
        "coverage": len(present) / expected,
        "expected_minutes": expected, "observed_minutes": len(present),
        "largest_gap": largest_gap,
    }


def session_candidates(bars, by_ts):
    output = {}
    first_day = bars[0].ts.date() - timedelta(days=35)
    last_day = bars[-1].ts.date() + timedelta(days=10)

    daily_sessions = []
    d = first_day
    while d <= last_day:
        if d.weekday() in (6, 0, 1, 2, 3):
            start = local_time(d, 17, 0, NY)
            end = local_time(d + timedelta(days=1), 17, 0, NY)
            q = period_quality(by_ts, start, end)
            if q:
                daily_sessions.append({"start": start, "end": end, **q})
        d += timedelta(days=1)

    cid = "NY17-DAILY-SHOCK-FADE-60"
    records, eligible, excluded, raw_signals = [], 0, 0, 0
    for i in range(20, len(daily_sessions)):
        cur, prior = daily_sessions[i], daily_sessions[i - 20:i]
        if minute_window(by_ts, cur["end"], EXPIRY_MINUTES) is None:
            excluded += 1
            continue
        eligible += 1
        threshold = 1.5 * sum(abs(x["log_return"]) for x in prior) / len(prior)
        if abs(cur["log_return"]) + 1e-15 < threshold:
            continue
        raw_signals += 1
        side = "PUT" if cur["log_return"] > 0 else "CALL"
        trade = make_trade(cid, cur["end"], cur["end"], by_ts, side, cur["log_return"], "NY 17:00 completed session")
        if trade:
            records.append(trade)
        else:
            excluded += 1
    output[cid] = {
        "label": "NY 17:00 daily shock fade", "records": records,
        "eligible_windows": eligible, "excluded_windows": excluded,
        "raw_signal_events": raw_signals,
        "rule": "Completed 17:00–17:00 New York session absolute log return >= 1.5x mean absolute return of preceding 20 valid sessions (current excluded); fade at next 17:00 NY open; 60-minute expiry.",
        "expiry_minutes": EXPIRY_MINUTES, "market_regime": "large completed NY trading-session move",
    }

    weekly_sessions = []
    d = first_day
    while d <= last_day:
        if d.weekday() == 6:
            start = local_time(d, 17, 0, NY)
            end = local_time(d + timedelta(days=5), 17, 0, NY)
            q = period_quality(by_ts, start, end)
            if q:
                weekly_sessions.append({"start": start, "end": end, **q})
        d += timedelta(days=1)

    cid = "NY17-WEEKLY-SHOCK-FADE-60"
    records, eligible, excluded, raw_signals = [], 0, 0, 0
    for i in range(13, len(weekly_sessions)):
        cur, prior = weekly_sessions[i], weekly_sessions[i - 13:i]
        next_start = cur["start"] + timedelta(days=7)
        if minute_window(by_ts, next_start, EXPIRY_MINUTES) is None:
            excluded += 1
            continue
        eligible += 1
        threshold = sum(abs(x["log_return"]) for x in prior) / len(prior)
        if abs(cur["log_return"]) + 1e-15 < threshold:
            continue
        raw_signals += 1
        side = "PUT" if cur["log_return"] > 0 else "CALL"
        trade = make_trade(cid, cur["end"], next_start, by_ts, side, cur["log_return"], "NY Sunday-to-Friday completed week")
        if trade:
            records.append(trade)
        else:
            excluded += 1
    output[cid] = {
        "label": "NY Sunday–Friday weekly shock fade", "records": records,
        "eligible_windows": eligible, "excluded_windows": excluded,
        "raw_signal_events": raw_signals,
        "rule": "Completed Sunday 17:00–Friday 17:00 New York session absolute log return >= 1.0x mean absolute return of preceding 13 valid weeks (current excluded); fade at next Sunday 17:00 NY open; 60-minute expiry.",
        "expiry_minutes": EXPIRY_MINUTES, "market_regime": "large completed NY trading-week move",
    }
    return output


def wilson(w, n):
    if n <= 0:
        return None
    z, p = 1.959963984540054, w / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [100 * (center - half), 100 * (center + half)]


def stats(records, outcome_key="outcome", payout=PAYOUT):
    rows = sorted(records, key=lambda r: r["entry_time"])
    values = [r[outcome_key] for r in rows]
    w, l, d = values.count("W"), values.count("L"), values.count("D")
    decisive = w + l
    net = w * payout - l
    gross_win, gross_loss = w * payout, l
    eq = peak = max_dd = 0.0
    streak = max_streak = 0
    for value in values:
        eq += payout if value == "W" else -1.0 if value == "L" else 0.0
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)
        streak = streak + 1 if value == "L" else 0
        max_streak = max(max_streak, streak)
    active_days = len({r["signal_time"].date().isoformat() for r in rows})
    return {
        "n": len(rows), "w": w, "l": l, "d": d, "decisive": decisive,
        "wr_pct": 100 * w / decisive if decisive else None,
        "wilson_95_pct": wilson(w, decisive), "net_units": net,
        "roi_pct": 100 * net / len(rows) if rows else None,
        "expectancy_units": net / len(rows) if rows else None,
        "profit_factor": gross_win / gross_loss if gross_loss else (None if not gross_win else "inf"),
        "max_drawdown_units": max_dd, "longest_losing_streak": max_streak,
        "active_days": active_days,
        "trades_per_active_day": len(rows) / active_days if active_days else 0.0,
    }


def percentile(values, q):
    if not values:
        return None
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def day_cluster_bootstrap(records):
    groups = defaultdict(list)
    for r in records:
        groups[r["signal_time"].date().isoformat()].append(r)
    days = sorted(groups)
    if len(days) < 2:
        return {"days": len(days), "replicates": 0, "wr_95_pct": None, "net_95_units": None}
    rng = random.Random(BOOTSTRAP_SEED)
    wrs, nets = [], []
    for _ in range(BOOTSTRAP_REPS):
        sample = []
        for _ in days:
            sample.extend(groups[rng.choice(days)])
        s = stats(sample)
        if s["wr_pct"] is not None:
            wrs.append(s["wr_pct"])
        nets.append(s["net_units"])
    return {
        "days": len(days), "replicates": BOOTSTRAP_REPS,
        "wr_95_pct": [percentile(wrs, 0.025), percentile(wrs, 0.975)] if wrs else None,
        "net_95_units": [percentile(nets, 0.025), percentile(nets, 0.975)] if nets else None,
    }


def split_records(records, d1, d2):
    splits = {"TRAIN": [], "VALIDATION": [], "TEST": []}
    purged = {"TRAIN": 0, "VALIDATION": 0}
    for r in records:
        sd, ed = r["signal_time"].date(), r["settle_time"].date()
        if sd < d1:
            if ed >= d1:
                purged["TRAIN"] += 1
            else:
                splits["TRAIN"].append(r)
        elif sd < d2:
            if ed >= d2:
                purged["VALIDATION"] += 1
            else:
                splits["VALIDATION"].append(r)
        else:
            splits["TEST"].append(r)
    return splits, purged


def fmt_pct(value):
    return "n/a" if value is None else f"{value:.2f}%"


def fmt_units(value):
    return "n/a" if value is None else f"{value:+.2f}u"


def build_report(candidates, data_meta, protocol_path, script_path, out_dir):
    first = datetime.fromisoformat(data_meta["first_utc"])
    last = datetime.fromisoformat(data_meta["last_utc"])
    span_days = (last.date() - first.date()).days
    d1 = first.date() + timedelta(days=int(span_days * 0.60))
    d2 = first.date() + timedelta(days=int(span_days * 0.80))
    out_dir.mkdir(parents=True, exist_ok=True)
    all_trades, result_manifest = [], []
    lines = [
        "# EUR/USD FX fixing and session-reversal discovery", "",
        f"- Captured UTC: {datetime.now(UTC).isoformat()}",
        "- Branch: hydra/research-validation",
        f"- Source: Dukascopy EUR/USD M1 BID; coverage {data_meta['first_utc']} — {data_meta['last_utc']}",
        f"- Raw M1 rows: {data_meta['raw_rows']:,}; valid unique: {data_meta['valid_unique_rows']:,}; invalid: {data_meta['invalid_rows']:,}; duplicate timestamps: {data_meta['duplicate_timestamp_rows']:,}",
        f"- Gaps: {data_meta['gap_intervals']:,} intervals; {data_meta['missing_m1_minutes']:,} missing minutes; largest missing interval {data_meta['largest_missing_interval_minutes']:,} minutes; continuity segments {data_meta['continuity_segments']:,}",
        f"- Raw CSV SHA-256: {data_meta['raw_csv_sha256']}",
        f"- Script SHA-256: {hashlib.sha256(script_path.read_bytes()).hexdigest()}",
        f"- Protocol SHA-256: {hashlib.sha256(protocol_path.read_bytes()).hexdigest()}",
        f"- Chronological calendar split: TRAIN before {d1}; VALIDATION {d1}–{d2 - timedelta(days=1)}; TEST from {d2}",
        "- TEST is from a historical source period previously inspected by other HydraAI screens; it is exploratory, not pristine independent confirmation.",
        "- Entry: exact next eligible M1 open; expiry: close of the 60th M1 candle from entry. Any missing minute in the 60-minute outcome window excludes the trade.",
        "- Payout accounting: WIN +0.92u, LOSS -1u, DRAW 0u; decisive break-even WR 52.0833%.",
        "- Matched control: opposite direction on the exact same candidate timestamps and prices.",
        "- All five rules were frozen before this run; no parameter sweep or TEST-based tuning was performed.",
        "- Dukascopy BID is not Pocket Option executable pricing; spread, quote construction, payout changes, latency and platform settlement are not modeled.", "",
        "## Candidate results", "",
        "| Candidate | Expiry | N | W/L/D | WR | Net @92% | Expectancy | Max DD | Longest L | VALIDATION N/WR/net | TEST N/WR/net | Status |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for cid, info in candidates.items():
        records = sorted(info["records"], key=lambda r: r["entry_time"])
        all_trades.extend(records)
        overall = stats(records)
        splits, purged = split_records(records, d1, d2)
        split_stats = {k: stats(v) for k, v in splits.items()}
        val, test = split_stats["VALIDATION"], split_stats["TEST"]
        breakeven = 100 * (1 / (1 + PAYOUT))
        if val["n"] < 30 or test["n"] < 30:
            status = "INSUFFICIENT_SAMPLE"
        elif (val["net_units"] > 0 and test["net_units"] > 0
              and val["wr_pct"] is not None and test["wr_pct"] is not None
              and val["wr_pct"] > breakeven and test["wr_pct"] > breakeven):
            status = "PRELIMINARY_LEAD"
        else:
            status = "NOT_PASS_PRIMARY_SCREEN"
        val_txt = f"{val['n']}/{fmt_pct(val['wr_pct'])}/{fmt_units(val['net_units'])}"
        test_txt = f"{test['n']}/{fmt_pct(test['wr_pct'])}/{fmt_units(test['net_units'])}"
        lines.append(
            f"| {cid} | {info['expiry_minutes']}m | {overall['n']} | "
            f"{overall['w']}/{overall['l']}/{overall['d']} | {fmt_pct(overall['wr_pct'])} | "
            f"{fmt_units(overall['net_units'])} | {fmt_units(overall['expectancy_units'])}/trade | "
            f"{overall['max_drawdown_units']:.2f}u | {overall['longest_losing_streak']} | "
            f"{val_txt} | {test_txt} | {status} |"
        )
        control = stats(records, "control_outcome")
        bootstrap = day_cluster_bootstrap(records)
        lines += [
            "", f"### {cid} — {info['label']}", "",
            f"- Exact rule: {info['rule']}",
            f"- Market regime: {info['market_regime']}",
            f"- Eligible windows: {info['eligible_windows']:,}; raw triggers: {info['raw_signal_events']:,}; accepted trades: {overall['n']:,}; excluded windows/trades: {info['excluded_windows']:,}.",
            f"- Signal share: {(100*overall['n']/info['eligible_windows'] if info['eligible_windows'] else 0):.3f}%; WAIT share: {(100*(1-overall['n']/info['eligible_windows']) if info['eligible_windows'] else 0):.3f}%.",
            f"- Overall: N={overall['n']}, W/L/D={overall['w']}/{overall['l']}/{overall['d']}, decisive WR={fmt_pct(overall['wr_pct'])}, Wilson 95%={overall['wilson_95_pct']}, net={fmt_units(overall['net_units'])}, ROI={fmt_pct(overall['roi_pct'])}, expectancy={fmt_units(overall['expectancy_units'])}/trade, PF={overall['profit_factor']}, max DD={overall['max_drawdown_units']:.2f}u, longest loss streak={overall['longest_losing_streak']}.",
            f"- Matched continuation control on same timestamps: N={control['n']}, W/L/D={control['w']}/{control['l']}/{control['d']}, WR={fmt_pct(control['wr_pct'])}, net={fmt_units(control['net_units'])}.",
            f"- Day-cluster bootstrap ({BOOTSTRAP_REPS:,} reps, seed {BOOTSTRAP_SEED}): {bootstrap}.",
            f"- Split purges: TRAIN={purged['TRAIN']}, VALIDATION={purged['VALIDATION']}.", "",
            "| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |",
            "|---|---:|---|---:|---|---:|---:|---:|---:|---:|",
        ]
        for split_name in ("TRAIN", "VALIDATION", "TEST"):
            s = split_stats[split_name]
            lines.append(
                f"| {split_name} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {fmt_pct(s['wr_pct'])} | "
                f"{s['wilson_95_pct']} | {fmt_units(s['net_units'])} | {fmt_pct(s['roi_pct'])} | "
                f"{s['profit_factor']} | {s['max_drawdown_units']:.2f}u | {s['longest_losing_streak']} |"
            )
        lines += ["", "| Payout | Net units |", "|---:|---:|"]
        for payout in PAYOUT_GRID:
            lines.append(f"| {payout:.0%} | {stats(records, payout=payout)['net_units']:+.2f} |")
        months = defaultdict(list)
        for r in records:
            months[r["signal_time"].strftime("%Y-%m")].append(r)
        lines += ["", "| UTC month | N | W/L/D | WR | Net @92% |", "|---|---:|---|---:|---:|"]
        for month in sorted(months):
            s = stats(months[month])
            lines.append(f"| {month} | {s['n']} | {s['w']}/{s['l']}/{s['d']} | {fmt_pct(s['wr_pct'])} | {s['net_units']:+.2f}u |")
        result_manifest.append({
            "candidate_id": cid, "rule": info["rule"], "market_regime": info["market_regime"],
            "expiry_minutes": info["expiry_minutes"], "eligible_windows": info["eligible_windows"],
            "raw_signal_events": info["raw_signal_events"], "excluded_windows": info["excluded_windows"],
            "overall": overall, "matched_continuation_control": control, "splits": split_stats,
            "purged": purged, "bootstrap": bootstrap, "status": status,
        })
    trades_path = out_dir / "trades.csv"
    fields = ["candidate_id", "signal_time", "entry_time", "settle_time", "side",
              "control_side", "outcome", "control_outcome", "entry_price", "exit_price",
              "pre_move_log_return", "event_label"]
    with trades_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in sorted(all_trades, key=lambda x: (x["candidate_id"], x["entry_time"])):
            writer.writerow({k: (r[k].isoformat() if isinstance(r[k], datetime) else r[k]) for k in fields})
    passed = [x["candidate_id"] for x in result_manifest if x["status"] == "PRELIMINARY_LEAD"]
    lines += [
        "", "## Primary screening outcome", "",
        f"- Preliminary leads passing the fixed screen: {len(passed)}/5 — {', '.join(passed) if passed else 'none'}.",
        "- A passing row is only a preliminary historical lead. The source period was previously inspected by other research; no row is independently confirmed. Fresh prospective observations and Pocket Option DEMO quote/settlement validation remain mandatory.",
        "- Do not fill a five-candidate batch with under-sampled or negative rows.", "",
        "## Interpretation limits", "",
        "- Wilson intervals assume independent trades. Day-cluster bootstrap preserves within-day clustering but does not remove multi-day dependence or broad research-selection bias.",
        "- The five candidate families are not pooled. The matched continuation control is the opposite direction at identical timestamps, not a randomized experiment.",
        "- M1 BID candles do not model the Pocket Option executable quote, spread, latency, payout variation or platform settlement. A positive historical proxy result is not a claim of platform profitability.", "",
        "## Reproducibility", "", "- Machine-readable manifest: manifest.json", "- Trade-level ledger: trades.csv", "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "captured_at_utc": datetime.now(UTC).isoformat(), "branch": "hydra/research-validation",
        "protocol": "research-artifacts/fixing-reversal-discovery-protocol-v1.md",
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        "data": data_meta,
        "split_boundaries": {"train_end_exclusive": d1.isoformat(), "validation_end_exclusive": d2.isoformat()},
        "payout": PAYOUT, "expiry_minutes": EXPIRY_MINUTES,
        "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_seed": BOOTSTRAP_SEED,
        "candidate_results": result_manifest, "preliminary_leads": passed,
        "batch_ready": len(passed) >= 5,
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
    candidates.update(fixing_candidates(bars, by_ts))
    candidates.update(session_candidates(bars, by_ts))
    manifest = build_report(candidates, meta, args.protocol, Path(__file__), args.out_dir)
    print(
        f"FX fixing/session screen complete: valid M1={meta['valid_unique_rows']:,}; "
        f"candidates={len(manifest['candidate_results'])}; preliminary leads={len(manifest['preliminary_leads'])}; "
        f"report={args.out_dir / 'report.md'}"
    )


if __name__ == "__main__":
    main()
