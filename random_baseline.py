import glob
import os
import numpy as np
import pandas as pd

PAYOUT = 0.80
SIMULATIONS = 1000
SEED = 42

rng = np.random.default_rng(SEED)
files = sorted(glob.glob("backtest_v2_holdout_*min.csv"))

if not files:
    raise SystemExit("Не найдены HOLDOUT CSV-файлы.")

for filename in files:
    df = pd.read_csv(filename)

    required = {"direction", "entry_price", "exit_price", "profit_units"}
    if not required.issubset(df.columns):
        print(f"Пропуск {filename}: не хватает столбцов.")
        continue

    change = (
        df["exit_price"].to_numpy(dtype=float)
        - df["entry_price"].to_numpy(dtype=float)
    )
    actual_profit = float(df["profit_units"].sum())

    wins = np.zeros(SIMULATIONS, dtype=int)
    profits = np.zeros(SIMULATIONS, dtype=float)

    for i in range(SIMULATIONS):
        call = rng.integers(0, 2, size=len(change)).astype(bool)
        win = ((call) & (change > 0)) | ((~call) & (change < 0))
        draw = change == 0

        wins[i] = int(win.sum())
        profits[i] = (
            win.sum() * PAYOUT
            - ((~win) & (~draw)).sum()
        )

    print(f"\n{os.path.basename(filename)}")
    print(f"Сделок: {len(df)}")
    print(f"Прибыль стратегии: {actual_profit:.2f}")
    print(f"Средняя случайная прибыль: {profits.mean():.2f}")
    print(f"5–95% случайной прибыли: "
          f"{np.percentile(profits, 5):.2f} .. "
          f"{np.percentile(profits, 95):.2f}")
    print(f"Случайных прогонов с прибылью не хуже стратегии: "
          f"{(profits <= actual_profit).mean() * 100:.1f}%")