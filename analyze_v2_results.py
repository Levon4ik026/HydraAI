import glob
import os
import pandas as pd

PAYOUT = 0.80

files = glob.glob("backtest_v2_*.csv")
files = [
    f for f in files
    if "_early_" in f or "_holdout_" in f
]

results = []

for filename in sorted(files):
    df = pd.read_csv(filename)

    required = {"direction", "outcome", "profit_units"}
    if not required.issubset(df.columns):
        print(f"Пропущен файл {filename}: нет нужных столбцов")
        continue

    period = "EARLY" if "_early_" in filename else "HOLDOUT"

    horizon = os.path.basename(filename).split("_")[-1]
    horizon = horizon.replace(".csv", "")

    for direction in ["CALL", "PUT"]:
        part = df[df["direction"] == direction]

        if part.empty:
            continue

        wins = int((part["outcome"] == "WIN").sum())
        losses = int((part["outcome"] == "LOSS").sum())
        draws = int((part["outcome"] == "DRAW").sum())

        decisive = wins + losses
        win_rate = (
            wins / decisive * 100
            if decisive else 0.0
        )

        profit = float(part["profit_units"].sum())

        results.append({
            "period": period,
            "horizon": horizon,
            "direction": direction,
            "trades": len(part),
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate_pct": round(win_rate, 2),
            "profit_units": round(profit, 2),
        })

result = pd.DataFrame(results)

if result.empty:
    print("Не удалось получить статистику.")
else:
    result["period_order"] = result["period"].map({
        "EARLY": 0,
        "HOLDOUT": 1,
    })

    result["horizon_order"] = result["horizon"].map({
        "1min": 1,
        "3min": 3,
        "5min": 5,
        "10min": 10,
    })

    result = result.sort_values(
        ["period_order", "horizon_order", "direction"]
    )

    print("\nHYDRA AI TRADER — CALL vs PUT")
    print(result.drop(
        columns=["period_order", "horizon_order"]
    ).to_string(index=False))

    result.to_csv(
        "backtest_v2_call_put_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("\nСохранено: backtest_v2_call_put_summary.csv")