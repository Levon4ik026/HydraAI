from pathlib import Path

import pandas as pd

FILE_NAME = "eurusd_history_extended.csv"
PAYOUT = 0.80
HORIZONS = [1, 3, 5, 10]
TRAIN_SHARE = 0.70

OUTPUT_PREFIX = "backtest_v2"

def load_data():
    path = Path(FILE_NAME)

    if not path.exists():
        raise FileNotFoundError(
            f"Не найден файл: {path.resolve()}"
        )

    df = pd.read_csv(path)

    required = [
        "datetime", "open", "high", "low", "close"
    ]

    missing = [
        col for col in required if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Отсутствуют колонки: {missing}"
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"], errors="coerce", utc=True
    )

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    df = df.dropna(subset=required)
    df = df.sort_values("datetime")
    df = df.drop_duplicates("datetime")
    df = df.reset_index(drop=True)

    if len(df) < 200:
        raise ValueError(
            "Недостаточно исторических данных."
        )

    return df

def calculate_rsi(close, period=14):
    delta = close.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = losses.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0), 100
    )

    rsi = rsi.mask(
        (avg_gain == 0) & (avg_loss == 0), 50
    )

    return rsi

def prepare_data(df):
    df = df.copy()

    df["EMA20"] = df["close"].ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50, adjust=False
    ).mean()

    df["RSI14"] = calculate_rsi(df["close"])

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

    # Разрыв между минутными свечами.
    df["gap_before"] = (
        df["datetime"].diff()
        != pd.Timedelta(minutes=1)
    )

    return df

def run_backtest(df, horizon):
    df = df.reset_index(drop=True)
    trades = []

    # Сигнал на свече i.
    # Вход на открытии свечи i+1.
    # Выход на закрытии свечи i+horizon.
    for i in range(len(df) - horizon):
        signal = int(df["signal"].iloc[i])

        if signal == 0:
            continue

        entry_index = i + 1
        exit_index = i + horizon

        # Не используем сделку, если внутри
        # её интервала отсутствует минутная свеча.
        interval = df.iloc[i + 1:exit_index + 1]

        if interval["gap_before"].any():
            continue

        entry_price = float(
            df.at[entry_index, "open"]
        )

        exit_price = float(
            df.at[exit_index, "close"]
        )

        if entry_price <= 0:
            continue

        change = exit_price - entry_price

        if abs(change) < 1e-12:
            outcome = "DRAW"
            profit = 0.0

        elif (
            signal == 1 and change > 0
        ) or (
            signal == -1 and change < 0
        ):
            outcome = "WIN"
            profit = PAYOUT

        else:
            outcome = "LOSS"
            profit = -1.0

        trades.append({
            "signal_time": df.at[i, "datetime"],
            "entry_time": df.at[entry_index, "datetime"],
            "exit_time": df.at[exit_index, "datetime"],
            "direction": (
                "CALL" if signal == 1 else "PUT"
            ),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "outcome": outcome,
            "profit_units": profit
        })

    return pd.DataFrame(trades)

def summarize(trades, period, horizon):
    if trades.empty:
        wins = 0
        losses = 0
        draws = 0
        win_rate = 0.0
        profit = 0.0
        max_drawdown = 0.0

    else:
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
        drawdown = equity.cummax() - equity
        max_drawdown = float(drawdown.max())

        profit = float(
            trades["profit_units"].sum()
        )

    return {
        "period": period,
        "horizon": horizon,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate_pct": round(win_rate, 4),
        "profit_units": round(profit, 4),
        "max_drawdown_units": round(
            max_drawdown, 4
        )
    }

def main():
    df = prepare_data(load_data())

    split_index = int(len(df) * TRAIN_SHARE)

    print("HYDRA AI TRADER — BACKTEST V2")
    print("Всего свечей:", len(df))
    print("Начало:", df["datetime"].iloc[0])
    print("Конец:", df["datetime"].iloc[-1])
    print(
        "Разрывов минут:",
        int(df["gap_before"].sum())
    )

    # Индикаторы рассчитаны до разделения,
    # но используют только текущие и прошлые цены.
    early = df.iloc[:split_index].copy()
    holdout = df.iloc[split_index:].copy()

    print("EARLY:", len(early), "свечей")
    print("HOLDOUT:", len(holdout), "свечей")

    results = []

    for horizon in HORIZONS:
        early_trades = run_backtest(
            early, horizon
        )

        holdout_trades = run_backtest(
            holdout, horizon
        )

        results.append(
            summarize(
                early_trades, "EARLY", horizon
            )
        )

        results.append(
            summarize(
                holdout_trades, "HOLDOUT", horizon
            )
        )

        if not early_trades.empty:
            early_trades.to_csv(
                f"{OUTPUT_PREFIX}_early_{horizon}min.csv",
                index=False
            )

        if not holdout_trades.empty:
            holdout_trades.to_csv(
                f"{OUTPUT_PREFIX}_holdout_{horizon}min.csv",
                index=False
            )

    summary = pd.DataFrame(results)

    summary.to_csv(
        f"{OUTPUT_PREFIX}_summary.csv",
        index=False
    )

    print("\nИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print(summary.to_string(index=False))

    print(
        f"\nСохранено: {OUTPUT_PREFIX}_summary.csv"
    )

if __name__ == "__main__":
    main()