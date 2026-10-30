import pandas as pd
FILE_NAME = "eurusd_history_10000.csv"
PAYOUT = 0.80
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
        "datetime", "open", "high", "low", "close"
    ]
    missing = [
        col for col in required if col not in df.columns
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
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )
    df = df.dropna(subset=required)
    df = df.sort_values("datetime")
    df = df.drop_duplicates("datetime")
    df = df.reset_index(drop=True)
    if len(df) < 200:
        raise ValueError("Недостаточно свечей для теста.")
    prices = df[["open", "high", "low", "close"]]
    if (prices <= 0).any().any():
        raise ValueError("Найдены нулевые или отрицательные цены.")
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
    # Берём только начало серии сигналов.
    # Например, CALL, CALL, CALL -> один вход на первом CALL.
    previous_signal = 0
    next_available_entry = 0
    for i in range(len(df) - horizon):
        signal = int(df.at[i, "signal"])
        # Сигнал должен появиться после отсутствия сигнала
        # или после смены направления.
        is_new_signal = (
            signal != 0 and signal != previous_signal
        )
        previous_signal = signal
        if not is_new_signal:
            continue
        entry_index = i + 1
        exit_index = entry_index + horizon - 1
        # Не открываем новую сделку, пока предыдущая
        # не завершилась.
        if entry_index < next_available_entry:
            continue
        if exit_index >= len(df):
            continue
        entry_price = float(df.at[entry_index, "open"])
        exit_price = float(df.at[exit_index, "close"])
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
            "signal_time": df.at[i, "datetime"],
            "entry_time": df.at[entry_index, "datetime"],
            "exit_time": df.at[exit_index, "datetime"],
            "direction": "CALL" if signal == 1 else "PUT",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "outcome": outcome,
            "profit_units": profit
        })
        next_available_entry = exit_index + 1
    return pd.DataFrame(trades)
def report_group(trades, direction):
    part = trades[trades["direction"] == direction]
    if part.empty:
        print(f"{direction}: сделок нет")
        return
    wins = int((part["outcome"] == "WIN").sum())
    losses = int((part["outcome"] == "LOSS").sum())
    draws = int((part["outcome"] == "DRAW").sum())
    decisive = wins + losses
    win_rate = wins / decisive * 100 if decisive else 0.0
    profit = float(part["profit_units"].sum())
    print(
        f"{direction}: сделок {len(part)}, "
        f"WIN {wins}, LOSS {losses}, DRAW {draws}, "
        f"win rate {win_rate:.2f}%, "
        f"результат {profit:.2f}"
    )
def main():
    print("=" * 65)
    print("HYDRA AI TRADER — FILTERED BACKTEST")
    print("=" * 65)
    df = prepare_indicators(load_data())
    print("Свечей:", len(df))
    print("Начало:", df["datetime"].iloc[0])
    print("Конец:", df["datetime"].iloc[-1])
    print("Выплата:", f"{PAYOUT:.0%}")
    print()
    summary = []
    for horizon in HORIZONS:
        trades = run_backtest(df, horizon)
        print("-" * 65)
        print(f"ЭКСПИРАЦИЯ: {horizon} мин.")
        print("Всего сделок:", len(trades))
        if trades.empty:
            continue
        wins = int((trades["outcome"] == "WIN").sum())
        losses = int((trades["outcome"] == "LOSS").sum())
        draws = int((trades["outcome"] == "DRAW").sum())
        decisive = wins + losses
        win_rate = wins / decisive * 100 if decisive else 0.0
        profit = float(trades["profit_units"].sum())
        equity = trades["profit_units"].cumsum()
        running_peak = equity.cummax().clip(lower=0)
        max_drawdown = float((running_peak - equity).max())
        print(f"WIN: {wins}")
        print(f"LOSS: {losses}")
        print(f"DRAW: {draws}")
        print(f"Процент побед без ничьих: {win_rate:.2f}%")
        print(f"Результат: {profit:.2f}")
        print(f"Максимальная просадка: {max_drawdown:.2f}")
        report_group(trades, "CALL")
        report_group(trades, "PUT")
        trades.to_csv(
            f"backtest_filtered_{horizon}min.csv",
            index=False
        )
        summary.append({
            "horizon": horizon,
            "trades": len(trades),
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate_pct": round(win_rate, 4),
            "profit_units": round(profit, 4),
            "max_drawdown_units": round(max_drawdown, 4)
        })
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(
        "backtest_filtered_summary.csv",
        index=False
    )
    print()
    print("=" * 65)
    print("СВОДНАЯ ТАБЛИЦА")
    print(summary_df.to_string(index=False))
    print()
    print("Сохранено: backtest_filtered_summary.csv")
    print("Это исследовательский тест, не гарантия прибыли.")
    print("=" * 65)
if __name__ == "__main__":
    main()