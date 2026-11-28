#!/usr/bin/env python3
"""Matched intraday event study for EUR/USD M1.
Run: python bls_fomc_matched_event_study.py eurusd_research_clean.csv --out research_output
Requires pandas and numpy. All times are America/New_York local release times.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

EVENTS = {
    "CPI": ("08:30", [
        "2025-08-12","2025-09-11","2025-10-24","2025-12-18",
        "2026-01-13","2026-02-13","2026-03-11","2026-04-10",
        "2026-05-12","2026-06-10","2026-07-14","2026-08-12",
        "2026-09-11","2026-10-14"]),
    "NFP": ("08:30", [
        "2025-09-05","2025-11-20","2025-12-16","2026-01-09",
        "2026-02-11","2026-03-06","2026-04-03","2026-05-08",
        "2026-06-05","2026-07-02","2026-08-07","2026-09-04",
        "2026-10-02"]),
    "PPI": ("08:30", [
        "2025-08-14","2025-09-10","2025-11-25","2026-01-14",
        "2026-01-30","2026-02-27","2026-03-18","2026-04-14",
        "2026-05-13","2026-06-11","2026-07-15","2026-08-13",
        "2026-09-10","2026-10-15"]),
    "FOMC_statement": ("14:00", [
        "2025-07-30","2025-09-17","2025-10-29","2025-12-10",
        "2026-01-28","2026-03-18","2026-04-29","2026-06-17",
        "2026-07-29","2026-09-16","2026-10-28"]),
    "FOMC_minutes": ("14:00", [
        "2025-08-20","2025-10-08","2025-11-19","2026-01-07",
        "2026-02-18","2026-04-08","2026-05-20","2026-07-08",
        "2026-08-19","2026-10-07"]),
}
HORIZONS = (5, 15, 30, 60)

def event_timestamp(date_et, time_et):
    return pd.Timestamp(f"{date_et} {time_et}", tz="America/New_York").tz_convert("UTC")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="EUR/USD M1 CSV with datetime_utc,open,high,low,close")
    ap.add_argument("--out", default="research_output")
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(args.csv)
    required = {"datetime_utc","open","high","low","close"}
    missing = required - set(data.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}")
    data["ts"] = pd.to_datetime(data["datetime_utc"], utc=True, errors="coerce")
    data = data.dropna(subset=["ts"]).sort_values("ts").drop_duplicates("ts").set_index("ts")
    if data.empty:
        raise SystemExit("No valid rows")

    def metrics(start, minutes):
        ix = pd.date_range(start, periods=minutes, freq="min")
        if not ix.isin(data.index).all():
            return None
        x = data.loc[ix]
        if len(x) != minutes:
            return None
        closes = x["close"].to_numpy(dtype=float)
        return {
            "path_pips": float(np.abs(np.diff(closes)).sum() * 10000),
            "range_pips": float((x["high"].max() - x["low"].min()) * 10000),
            "signed_pips": float((closes[-1] - float(x["open"].iloc[0])) * 10000),
            "up": bool(closes[-1] > float(x["open"].iloc[0])),
        }

    event_list = []
    for category, (clock, dates) in EVENTS.items():
        for date in dates:
            event_list.append({
                "category": category, "date_et": date, "time_et": clock,
                "event_utc": event_timestamp(date, clock)
            })
    events = pd.DataFrame(event_list)
    event_dates = {pd.Timestamp(d).date() for d in events["date_et"]}

    event_rows = []
    control_rows = []
    for event in events.to_dict("records"):
        t = event["event_utc"]
        pre = metrics(t - pd.Timedelta(minutes=30), 30)
        post = {n: metrics(t, n) for n in HORIZONS}
        if pre is None or any(v is None for v in post.values()):
            continue
        for n, m in post.items():
            event_rows.append({
                "category": event["category"], "date_et": event["date_et"],
                "time_et": event["time_et"], "event_utc": t.isoformat(),
                "horizon_min": n, "pre30_path_pips": pre["path_pips"], **m
            })

        # Matched controls: same weekday and ET release clock, within +/-35 calendar
        # days; exclude all dates on the compiled CPI/NFP/PPI/FOMC event ledger.
        day = pd.Timestamp(event["date_et"])
        candidates = []
        for delta in range(-35, 36):
            if delta == 0:
                continue
            candidate_day = (day + pd.Timedelta(days=delta)).date()
            if pd.Timestamp(candidate_day).weekday() != day.weekday():
                continue
            if candidate_day in event_dates:
                continue
            ct = event_timestamp(str(candidate_day), event["time_et"])
            cpre = metrics(ct - pd.Timedelta(minutes=30), 30)
            cpost = {n: metrics(ct, n) for n in HORIZONS}
            if cpre is None or any(v is None for v in cpost.values()):
                continue
            distance = abs(np.log((cpre["path_pips"] + 0.1) / (pre["path_pips"] + 0.1)))
            candidates.append((distance, ct, cpre, cpost))
        candidates.sort(key=lambda z: z[0])
        for rank, (_, ct, cpre, cpost) in enumerate(candidates[:3], start=1):
            for n, m in cpost.items():
                control_rows.append({
                    "category": event["category"], "event_date_et": event["date_et"],
                    "control_date_et": str(ct.tz_convert("America/New_York").date()),
                    "rank": rank, "horizon_min": n,
                    "pre30_path_pips": cpre["path_pips"], **m
                })

    ev = pd.DataFrame(event_rows)
    co = pd.DataFrame(control_rows)
    if ev.empty or co.empty:
        raise SystemExit("No complete event/control windows; inspect data coverage.")

    per_event_control = co.groupby(
        ["category","event_date_et","horizon_min"], as_index=False
    ).agg(
        control_path_pips=("path_pips","median"),
        control_range_pips=("range_pips","median"),
        control_signed_pips=("signed_pips","median"),
        control_up=("up","mean")
    )
    merged = ev.merge(
        per_event_control,
        left_on=["category","date_et","horizon_min"],
        right_on=["category","event_date_et","horizon_min"],
        how="inner"
    )
    summary = merged.groupby(["category","horizon_min"], as_index=False).agg(
        events=("date_et","count"),
        event_path_median=("path_pips","median"),
        control_path_median=("control_path_pips","median"),
        event_range_median=("range_pips","median"),
        control_range_median=("control_range_pips","median"),
        event_signed_median=("signed_pips","median"),
        control_signed_median=("control_signed_pips","median"),
        event_up_share=("up","mean"),
        control_up_share=("control_up","mean")
    )
    ev.to_csv(outdir / "event_windows.csv", index=False)
    co.to_csv(outdir / "matched_control_windows.csv", index=False)
    merged.to_csv(outdir / "event_vs_matched_controls.csv", index=False)
    summary.to_csv(outdir / "summary.csv", index=False)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nSaved outputs to {outdir.resolve()}")
    print(f"Events with complete 5/15/30/60m and pre30 windows: {ev[ev.horizon_min==60].groupby('category').size().to_dict()}")

if __name__ == "__main__":
    main()
