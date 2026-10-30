import pandas as pd
import numpy as np

FILE_NAME = "eurusd_history_extended.csv"
PAYOUT = 0.80
HORIZONS = [1, 3, 5, 10]
TRAIN_RATIO = 0.70

def load_data():
    df = pd.read_csv(FILE_NAME)

    df["datetime"] = pd.to_datetime(
        df["datetime"], utc=True
    )

    df = df.sort_values("datetime")
    df = df.drop_duplicates("datetime")
    df = df.reset_index(drop=True)

    df["EMA20"] = df["close"].ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50, adjust=False
    ).mean()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss

    df["RSI14"] = 100 - (100 / (1 + rs))

    df["signal"] = 0

    call = (
        (df["EMA20"] > df["EMA50"])
        & (df["RSI14"] >= 50)
        & (df["RSI14"] <= 65)
    )

    put = (
        (df["EMA20"] < df["EMA50"])
        & (df["RSI14"] >= 35)
        & (df["RSI14"] < 50)
    )

    df.loc[call, "signal"] = 1
    df.loc[put, "signal"] = -1

    df["gap_before"] = (
        df["datetime"].diff()
        != pd.Timedelta(minutes=1)
    )

    if len(df):
        df.loc[0, "gap_before"] = False

    return df

def backtest_non_overlapping(df, horizon, direction):
    trades = []

    i = 0
    last_index = len(df) - 1

    while i + horizon <= last_index:
        signal = int(df["signal"].iloc[i])

        if signal != direction:
            i += 1
            continue

        entry_index = i + 1
        exit_index = i + horizon

        interval = df.iloc[
            entry_index:exit_index + 1
        ]

        if interval["gap_before"].any():
            i += 1
            continue

        entry_price = float(
            df["open"].iloc[entry_index]
        )

        exit_price = float(
            df["close"].iloc[exit_index]
        )

        change = exit_price - entry_price

        if abs(change) < 1e-12:
            outcome = "DRAW"
            profit = 0.0

        elif (
            direction == 1 and change > 0
        ) or (
            direction == -1 and change < 0
        ):
            outcome = "WIN"
            profit = PAYOUT

        else:
            outcome = "LOSS"
            profit = -1.0

        trades.append({
            "signal_time": df["datetime"].iloc[i],
            "entry_time": df["datetime"].iloc[entry_index],
            "exit_time": df["datetime"].iloc[exit_index],
            "direction": (
                "CALL" if direction == 1 else "PUT"
            ),
            "outcome": outcome,
            "profit_units": profit,
        })

        # Следующий сигнал ищем только после завершения сделки.
        i = exit_index + 1

    return pd.DataFrame(trades)

def summarize(trades):
    if trades.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate_pct": 0.0,
            "profit_units": 0.0,
            "max_drawdown_units": 0.0,
        }

    wins = int(
        (trades["outcome"] == "WIN").sum()
    )

    losses = int(
        (trades["outcome"] == "LOSS").sum()
    )

    draws = int(
        (trades["outcome"] == "DRAW").sum()
    )

    decisive = wins + losses

    win_rate = (
        wins / decisive * 100
        if decisive else 0.0
    )

    equity = trades["profit_units"].cumsum()

    equity_with_start = pd.concat([
        pd.Series([0.0]),
        equity.reset_index(drop=True)
    ], ignore_index=True)

    drawdown = (
        equity_with_start.cummax()
        - equity_with_start
    )

    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate_pct": round(win_rate, 2),
        "profit_units": round(
            trades["profit_units"].sum(), 2
        ),
        "max_drawdown_units": round(
            drawdown.max(), 2


),
    }

def main():
    df = load_data()

    split_index = int(len(df) * TRAIN_RATIO)

    early = df.iloc[:split_index].copy()
    holdout = df.iloc[split_index:].copy()

    print("\nHYDRA AI TRADER — BACKTEST V3")
    print("Всего свечей:", len(df))
    print("EARLY:", len(early))
    print("HOLDOUT:", len(holdout))
    print("Режим: без пересекающихся сделок")

    results = []

    for period_name, part in [
        ("EARLY", early),
        ("HOLDOUT", holdout),
    ]:
        for horizon in HORIZONS:
            for direction in [1, -1]:
                trades = backtest_non_overlapping(
                    part, horizon, direction
                )

                direction_name = (
                    "CALL" if direction == 1 else "PUT"
                )

                filename = (
                    f"backtest_v3_{period_name.lower()}_"
                    f"{direction_name.lower()}_"
                    f"{horizon}min.csv"
                )

                trades.to_csv(
                    filename,
                    index=False,
                    encoding="utf-8-sig",
                )

                summary = summarize(trades)

                results.append({
                    "period": period_name,
                    "horizon_min": horizon,
                    "direction": direction_name,
                    **summary,
                })

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        "backtest_v3_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("\nИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print(result_df.to_string(index=False))

    print("\nСохранено: backtest_v3_summary.csv")

if __name__ == "__main__":
    main()