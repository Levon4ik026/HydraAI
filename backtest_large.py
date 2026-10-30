import pandas as pd

FILE_NAME = "eurusd_history_10000.csv"

# Предполагаемая чистая прибыль при выигрыше
# на одну условную единицу ставки.
PAYOUT = 0.80

# Экспирации в минутах.
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

    missing = [
        column for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"В CSV отсутствуют столбцы: {missing}"
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce",
        utc=True
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(subset=required)

    # Сортируем данные от старых свечей к новым.
    df = df.sort_values("datetime")

    # Оставляем только одну запись на каждую минуту.
    df = df.drop_duplicates(
        subset="datetime",
        keep="last"
    )

    df = df.reset_index(drop=True)

    if len(df) < 100:
        raise ValueError(
            f"Недостаточно данных: {len(df)} свечей."
        )

    # Проверяем, что OHLC-цены имеют допустимый порядок.
    invalid = (
        (df["open"] <= 0)
        | (df["high"] <= 0)
        | (df["low"] <= 0)
        | (df["close"] <= 0)
        | (df["high"] < df["low"])
        | (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
    )

    if invalid.any():
        raise ValueError(
            f"Обнаружены некорректные свечи: {int(invalid.sum())}. "
            "Проверь исходный CSV."
        )

    # Этот тест предполагает последовательные минутные свечи.
    minute_diffs = df["datetime"].diff().dropna()

    gaps = minute_diffs[
        minute_diffs != pd.Timedelta(minutes=1)
    ]

    if not gaps.empty:
        print(
            "ПРЕДУПРЕЖДЕНИЕ: найдены промежутки "
            "между свечами, отличающиеся от 1 минуты:",
            len(gaps)
        )
        print(
            "Проверим результаты осторожно: "
            "экспирация в строках может не совпадать "
            "с реальным временем."
        )

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

    df["RSI14"] = calculate_rsi(
        df["close"],
        period=14
    )

    # Сигнал формируется по закрытию текущей свечи.
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

    # Сигнал на свече i известен после её закрытия.
    # Вход — открытие следующей свечи.
    # Для горизонта N результат оценивается по закрытию
    # N-й свечи, считая свечу входа первой.
    for i in range(len(df) - horizon):
        signal = int(df.at[i, "signal"])

        if signal == 0:
            continue

        entry_index = i + 1
        exit_index = entry_index + horizon - 1

        if exit_index >= len(df):
            continue

        entry_price = float(
            df.at[entry_index, "open"]
        )

        exit_price = float(
            df.at[exit_index, "close"]
        )

        if entry_price <= 0:
            continue

        change = (
            exit_price - entry_price
        ) / entry_price

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
            "signal_time": df.at[i, "datetime"],
            "entry_time": df.at[entry_index, "datetime"],
            "exit_time": df.at[exit_index, "datetime"],
            "direction": "CALL" if signal == 1 else "PUT",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "price_change_pct": change * 100,
            "outcome": outcome,
            "profit_units": profit
        })

    return pd.DataFrame(trades)

def print_results(trades, horizon):
    print()
    print("-" * 60)
    print(f"ЭКСПИРАЦИЯ: {horizon} мин.")
    print("-" * 60)

    if trades.empty:
        print("Сделок по выбранным правилам нет.")
        return {
            "horizon": horizon,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate_pct": 0.0,
            "net_profit_units": 0.0,
            "max_drawdown_units": 0.0
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

    net_profit = float(
        trades["profit_units"].sum()
    )

    equity = trades["profit_units"].cumsum()

    # Просадка от предыдущего максимума кривой капитала.
    running_peak = equity.cummax().clip(lower=0)

    drawdown = running_peak - equity

    max_drawdown = float(
        drawdown.max()
    )

    print("Всего сделок:", len(trades))
    print("Выигрыши:", wins)
    print("Проигрыши:", losses)
    print("Ничьи:", draws)

    print(
        f"Процент выигрышей без ничьих: "
        f"{win_rate:.2f}%"
    )

    print(
        f"Условный чистый результат: "
        f"{net_profit:.2f} единиц ставки"
    )

    print(
        f"Максимальная просадка: "
        f"{max_drawdown:.2f} единиц ставки"
    )

    print(
        "Безубыточный процент выигрышей "
        f"при выплате {PAYOUT:.0%}: "
        f"{100 / (1 + PAYOUT):.2f}% "
        "(без учёта ничьих)"
    )

    # Дополнительная разбивка по направлениям.
    for direction in ["CALL", "PUT"]:
        part = trades[
            trades["direction"] == direction
        ]

        part_wins = int(
            (part["outcome"] == "WIN").sum()
        )

        part_losses = int(
            (part["outcome"] == "LOSS").sum()
        )

        part_draws = int(
            (part["outcome"] == "DRAW").sum()
        )

        part_decisive = part_wins + part_losses

        part_rate = (
            part_wins / part_decisive * 100
            if part_decisive else 0.0
        )

        part_profit = float(
            part["profit_units"].sum()
        )

        print(
            f"{direction}: сделок {len(part)}, "
            f"WIN {part_wins}, LOSS {part_losses}, "
            f"DRAW {part_draws}, "
            f"win rate {part_rate:.2f}%, "
            f"результат {part_profit:.2f}"
        )

    return {
        "horizon": horizon,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate_pct": round(win_rate, 4),
        "net_profit_units": round(net_profit, 4),
        "max_drawdown_units": round(max_drawdown, 4)
    }

def main():
    print("=" * 60)
    print("HYDRA AI TRADER — BACKTEST LARGE HISTORY")
    print("=" * 60)

    df = load_data()
    df = prepare_indicators(df)

    print("Файл:", FILE_NAME)
    print("Свечей загружено:", len(df))
    print(
        "Начало:",
        df["datetime"].iloc[0]
    )
    print(
        "Конец:",
        df["datetime"].iloc[-1]
    )
    print("Предполагаемая выплата:", f"{PAYOUT:.0%}")
    print(
        "Условия сигналов оставлены такими же, "
        "как в первоначальном тесте."
    )

    summary = []

    for horizon in HORIZONS:
        trades = run_backtest(
            df,
            horizon
        )

        result = print_results(
            trades,
            horizon
        )

        summary.append(result)

        output_file = (
            f"backtest_large_{horizon}min.csv"
        )

        trades.to_csv(
            output_file,
            index=False
        )

        print("Подробные сделки сохранены:", output_file)

    summary_df = pd.DataFrame(summary)

    summary_df.to_csv(
        "backtest_large_summary.csv",
        index=False
    )

    print()
    print("=" * 60)
    print("СВОДНАЯ ТАБЛИЦА")
    print("=" * 60)
    print(summary_df.to_string(index=False))

    print()
    print("Сводка сохранена: backtest_large_summary.csv")
    print(
        "Важно: это исторический исследовательский тест, "
        "а не гарантия будущей прибыли."
    )
    print("=" * 60)

if __name__ == "__main__":
    main() 