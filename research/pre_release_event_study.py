#!/usr/bin/env python3
"""Pre-release EUR/USD M1 event study with matched weekday controls.

Run:
  python research/pre_release_event_study.py eurusd_research_clean.csv --out research_output

Requires pandas and numpy. Event clocks are New York local time (DST-aware).
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

EVENTS = {
    "CPI": ("08:30", ["2025-08-12","2025-09-11","2025-10-24","2025-12-18",
        "2026-01-13","2026-02-13","2026-03-11","2026-04-10","2026-05-12",
        "2026-06-10","2026-07-14","2026-08-12","2026-09-11","2026-10-14"]),
    "NFP": ("08:30", ["2025-09-05","2025-11-20","2025-12-16","2026-01-09",
        "2026-02-11","2026-03-06","2026-04-03","2026-05-08","2026-06-05",
        "2026-07-02","2026-08-07","2026-09-04","2026-10-02"]),
    "PPI": ("08:30", ["2025-08-14","2025-09-10","2025-11-25","2026-01-14",
        "2026-01-30","2026-02-27","2026-03-18","2026-04-14","2026-05-13",
        "2026-06-11","2026-07-15","2026-08-13","2026-09-10","2026-10-15"]),
    "FOMC_statement": ("14:00", ["2025-07-30","2025-09-17","2025-10-29",
        "2025-12-10","2026-01-28","2026-03-18","2026-04-29","2026-06-17",
        "2026-07-29","2026-09-16","2026-10-28"]),
    "FOMC_minutes": ("14:00", ["2025-08-20","2025-10-08","2025-11-19",
        "2026-01-07","2026-02-18","2026-04-08","2026-05-20","2026-07-08",
        "2026-08-19","2026-10-07"]),
}
WINDOWS = {
    "pre60": (-60, 0), "pre30": (-30, 0), "pre15": (-15, 0),
    "pre60_30": (-60, -30), "pre30_15": (-30, -15),
    "pre15_0": (-15, 0), "baseline": (-180, -120),
}
FIELDS = ("path", "range", "signed", "up")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV with datetime_utc,open,high,low,close")
    ap.add_argument("--out", default="research_output")
    args = ap.parse_args()

    frame = pd.read_csv(args.csv)
    required = {"datetime_utc", "open", "high", "low", "close"}
    if required - set(frame.columns):
        raise SystemExit(f"Missing columns: {sorted(required - set(frame.columns))}")
    frame["ts"] = pd.to_datetime(frame["datetime_utc"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["ts"]).sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    timestamps = frame["ts"].astype("int64").to_numpy()
    position = {value: i for i, value in enumerate(timestamps)}
    op, hi, lo, cl = (frame[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close"))

    def event_utc(date, clock):
        return pd.Timestamp(f"{date} {clock}", tz="America/New_York").tz_convert("UTC").value

    def metric(t_ns, start_min, end_min):
        first = position.get(t_ns + start_min * 60 * 10**9)
        if first is None:
            return None
        count = end_min - start_min
        last = first + count - 1
        if last >= len(timestamps) or timestamps[last] != t_ns + (end_min - 1) * 60 * 10**9:
            return None
        ix = slice(first, last + 1)
        closes = cl[ix]
        return (
            float(np.abs(np.diff(closes)).sum() * 10000),
            float((hi[ix].max() - lo[ix].min()) * 10000),
            float((closes[-1] - op[first]) * 10000),
            bool(closes[-1] > op[first]),
        )

    event_dates = {pd.Timestamp(d).date() for _, dates in EVENTS.values() for d in dates}
    event_rows, control_rows = [], []
    for category, (clock, dates) in EVENTS.items():
        for date in dates:
            t = event_utc(date, clock)
            values = {name: metric(t, *window) for name, window in WINDOWS.items()}
            if any(value is None for value in values.values()):
                continue
            row = {"category": category, "event_date": date}
            for name, value in values.items():
                row.update({f"{name}_{field}": item for field, item in zip(FIELDS, value)})
            event_rows.append(row)

            day = pd.Timestamp(date)
            candidates = []
            for delta in range(-35, 36):
                if delta == 0:
                    continue
                control_date = (day + pd.Timedelta(days=delta)).date()
                if pd.Timestamp(control_date).weekday() != day.weekday() or control_date in event_dates:
                    continue
                ct = event_utc(str(control_date), clock)
                baseline = metric(ct, -180, -120)
                windows = {name: metric(ct, *window) for name, window in WINDOWS.items() if name != "baseline"}
                if baseline is None or any(value is None for value in windows.values()):
                    continue
                distance = abs(np.log((baseline[0] + 0.1) / (values["baseline"][0] + 0.1)))
                candidates.append((distance, control_date, windows))
            for rank, (_, control_date, windows) in enumerate(sorted(candidates, key=lambda x: x[0])[:3], 1):
                row = {"category": category, "event_date": date, "control_date": str(control_date), "rank": rank}
                for name, value in windows.items():
                    row.update({f"{name}_{field}": item for field, item in zip(FIELDS, value)})
                control_rows.append(row)

    events = pd.DataFrame(event_rows)
    controls = pd.DataFrame(control_rows)
    if events.empty or controls.empty:
        raise SystemExit("No complete event/control windows.")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    events.to_csv(out / "pre_release_event_windows.csv", index=False)
    controls.to_csv(out / "pre_release_matched_controls.csv", index=False)

    print("Complete event counts:", events.groupby("category").size().to_dict())
    for category in EVENTS:
        e = events[events.category == category]
        c = controls[controls.category == category]
        print(f"\n{category} (n={len(e)})")
        for window in ("pre60", "pre30", "pre15", "pre60_30", "pre30_15"):
            matched = c.groupby("event_date").agg(
                path=(f"{window}_path", "median"),
                signed=(f"{window}_signed", "median"),
                up=(f"{window}_up", "mean"),
            )
            print(
                f"{window}: path {e[f'{window}_path'].median():.2f}/{matched.path.median():.2f}; "
                f"signed {e[f'{window}_signed'].median():.2f}/{matched.signed.median():.2f}; "
                f"up {e[f'{window}_up'].mean():.1%}/{matched.up.mean():.1%} (event/control)"
            )
    print(f"\nSaved CSV outputs to {out.resolve()}")


if __name__ == "__main__":
    main()
