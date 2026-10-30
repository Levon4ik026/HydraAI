import pandas as pd

FILE_NAME = "eurusd_history.csv"

# Предполагаемая выплата: 80% чистой прибыли
# при выигрыше на единицу ставки.
PAYOUT = 0.80

# Сроки экспирации в минутах.
HORIZONS = [1, 3, 5, 10]

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
        "datetime",
        "open",
        "high",
        "low",
        "close"
    ]

    if not all(column in df.columns for column in required):
        raise ValueError("В CSV отсутствуют необходимые столбцы.")

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce"
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(subset=required)
    df = df.sort_values("datetime")
    df = df.drop_duplicates(subset="datetime")
    df = df.reset_index(drop=True)

    if len(df) < 100:
        raise ValueError("Недостаточно свечей для тестирования.")

    return df

def prepare_indicators(df):
    df = df.copy()

    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    df["RSI14"] = calculate_rsi(df["close"])

    # Сигнал определяется по закрытию текущей свечи.
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

    # Вход условно производится по цене открытия
    # следующей свечи после формирования сигнала.
    # Результат оценивается по цене закрытия
    # свечи через выбранный горизонт.
    for i in range(len(df) - horizon - 1):
        signal = int(df.loc[i, "signal"])

        if signal == 0:
            continue

        entry_index = i + 1
        exit_index = entry_index + horizon - 1

        entry_price = float(df.loc[entry_index, "open"])
        exit_price = float(df.loc[exit_index, "close"])

        if entry_price <= 0:
            continue

        change = (exit_price - entry_price) / entry_price

        if abs(change) < 1e-12:
            outcome = "DRAW"
            profit = 0.0
        elif (signal == 1 and change > 0) or (
            signal == -1 and change < 0
        ):
            outcome = "WIN"
            profit = PAYOUT
        else:
            outcome = "LOSS"
            profit = -1.0

        trades.append({
            "signal_time": df.loc[i, "datetime"],
            "entry_time": df.loc[entry_index, "datetime"],
            "exit_time": df.loc[exit_index, "datetime"],
            "direction": "CALL" if signal == 1 else "PUT",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "outcome": outcome,
            "profit_units": profit
        })

    return pd.DataFrame(trades)

def main():
    print("=" * 55)
    print("HYDRA AI TRADER — HISTORICAL BACKTEST")
    print("=" * 55)

    df = load_data()
    df = prepare_indicators(df)

    print("Свечей загружено:", len(df))
    print("Период:", df["datetime"].iloc[0], "—", df["datetime"].iloc[-1])
    print("Предполагаемая выплата:", f"{PAYOUT:.0%}")
    print()

    for horizon in HORIZONS:
        trades = run_backtest(df, horizon)

        print("-" * 55)
        print(f"Горизонт: {horizon} мин.")

        if trades.empty:
            print("Сделок по выбранным правилам нет.")
            continue

        wins = int((trades["outcome"] == "WIN").sum())
        losses = int((trades["outcome"] == "LOSS").sum())
        draws = int((trades["outcome"] == "DRAW").sum())

        decisive = wins + losses
        win_rate = wins / decisive * 100 if decisive else 0.0

        net_profit = trades["profit_units"].sum()

        equity = trades["profit_units"].cumsum()
        drawdown = equity.cummax() - equity
        max_drawdown = drawdown.max()

        print("Всего сделок:", len(trades))
        print("Выигрыши:", wins)
        print("Проигрыши:", losses)
        print("Ничьи:", draws)
        print(f"Процент выигрышей без ничьих: {win_rate:.2f}%")
        print(f"Условный результат: {net_profit:.2f} единиц ставки")
        print(f"Максимальная просадка по последовательности сделок: {max_drawdown:.2f}")

        # Сохраняем подробности для дальнейшего анализа.
        trades.to_csv(
            f"backtest_{horizon}min.csv",
            index=False
        )

    print()
    print("Тест завершён.")
    print("Подробные результаты сохранены в CSV.")
    print("Это исследовательский тест, не прогноз прибыли.")
    print("=" * 55)

if __name__ == "__main__":
    main()