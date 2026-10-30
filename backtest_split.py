import pandas as pd

FILE_NAME = "eurusd_history_10000.csv"
PAYOUT = 0.80
HORIZONS = [1, 3, 5, 10]

# Первые 70% истории — исследовательская часть.
# Последние 30% — проверочная часть.
TRAIN_SHARE = 0.70

def calculate_rsi(series, period=14):
    delta = series.diff()
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
    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0),
        100
    )
    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain == 0),
        50
    )

    return rsi

def load_data():
    df = pd.read_csv(FILE_NAME)

    required = [
        "datetime", "open", "high", "low", "close"
    ]

    missing = [
        col for col in required if col not in df.columns
    ]
    if missing:
        raise ValueError(f"Не найдены столбцы: {missing}")

    df["datetime"] = pd.to_datetime(
        df["datetime"], errors="coerce", utc=True
    )

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)
    df = df.sort_values("datetime")
    df = df.drop_duplicates("datetime")
    df = df.reset_index(drop=True)

    if len(df) < 200:
        raise ValueError("Недостаточно данных для теста.")

    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Найдены нулевые или отрицательные цены.")

    return df

def prepare_indicators(df):
    df = df.copy()

    df["EMA20"] = df["close"].ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50, adjust=False
    ).mean()

    df["RSI14"] = calculate_rsi(df["close"])

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

    df["signal"] = 0
    df.loc[call, "signal"] = 1
    df.loc[put, "signal"] = -1

    return df

def run_backtest(df, horizon):
    trades = []

    for i in range(len(df) - horizon):
        signal = int(df.iloc[i]["signal"])

        if signal == 0:
            continue

        entry_index = i + 1
        exit_index = entry_index + horizon - 1

        if exit_index >= len(df):
            continue

        entry_price = float(df.iloc[entry_index]["open"])
        exit_price = float(df.iloc[exit_index]["close"])

        if entry_price <= 0:
            continue

        change = (exit_price - entry_price) / entry_price

        if abs(change) < 1e-12:
            outcome = "DRAW"
            profit = 0.0
        elif (
            (signal == 1 and change > 0)
            or (signal == -1 and change < 0)
        ):
            outcome = "WIN"
            profit = PAYOUT
        else:
            outcome = "LOSS"
            profit = -1.0

        trades.append({
            "signal_time": df.iloc[i]["datetime"],
            "entry_time": df.iloc[entry_index]["datetime"],
            "exit_time": df.iloc[exit_index]["datetime"],
            "direction": "CALL" if signal == 1 else "PUT",
            "outcome": outcome,
            "profit_units": profit
        })

    return pd.DataFrame(trades)

def summarize(trades, label, horizon):
    if trades.empty:
        return {
            "period": label,
            "horizon": horizon,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate_pct": 0.0,
            "profit_units": 0.0
        }

    wins = int((trades["outcome"] == "WIN").sum())
    losses = int((trades["outcome"] == "LOSS").sum())
    draws = int((trades["outcome"] == "DRAW").sum())

    decisive = wins + losses
    win_rate = wins / decisive * 100 if decisive else 0.0
    profit = float(trades["profit_units"].sum())

    print(


f"{label} | {horizon} мин | "
        f"сделок: {len(trades)} | "
        f"W/L/D: {wins}/{losses}/{draws} | "
        f"win rate: {win_rate:.2f}% | "
        f"результат: {profit:.2f}"
    )

    return {
        "period": label,
        "horizon": horizon,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate_pct": round(win_rate, 4),
        "profit_units": round(profit, 4)
    }

def main():
    print("=" * 65)
    print("HYDRA AI TRADER — CHRONOLOGICAL HOLDOUT TEST")
    print("=" * 65)

    df = load_data()
    df = prepare_indicators(df)

    split_index = int(len(df) * TRAIN_SHARE)

    # Границу определяем по времени, а не случайным перемешиванием.
    train = df.iloc[:split_index].copy()
    test = df.iloc[split_index:].copy()

    print("Всего свечей:", len(df))
    print(
        "Ранняя часть:",
        train["datetime"].iloc[0],
        "—",
        train["datetime"].iloc[-1],
        "| свечей:",
        len(train)
    )
    print(
        "Проверочная часть:",
        test["datetime"].iloc[0],
        "—",
        test["datetime"].iloc[-1],
        "| свечей:",
        len(test)
    )
    print()
    print(
        "Важно: правила не подбираются на проверочной части. "
        "Она используется только для оценки."
    )
    print()

    results = []

    for horizon in HORIZONS:
        # В обучающей части используем только её собственные свечи.
        train_trades = run_backtest(train, horizon)

        # Индикаторы проверочной части рассчитаны на полной истории:
        # это допустимо, поскольку EMA/RSI используют прошлые свечи.
        # Однако сделки оцениваются только внутри test.
        test_trades = run_backtest(test, horizon)

        results.append(
            summarize(train_trades, "EARLY", horizon)
        )
        results.append(
            summarize(test_trades, "HOLDOUT", horizon)
        )

        train_trades.to_csv(
            f"backtest_split_early_{horizon}min.csv",
            index=False
        )
        test_trades.to_csv(
            f"backtest_split_holdout_{horizon}min.csv",
            index=False
        )

    summary = pd.DataFrame(results)
    summary.to_csv("backtest_split_summary.csv", index=False)

    print()
    print("=" * 65)
    print("СВОДКА")
    print("=" * 65)
    print(summary.to_string(index=False))
    print()
    print("Сохранено: backtest_split_summary.csv")
    print("Проверочная часть не доказывает будущую прибыльность.")
    print("=" * 65)

if __name__ == "__main__":
    main()