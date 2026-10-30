import pandas as pd
FILE_NAME = "eurusd_history_10000.csv"
PAYOUT = 0.80
HORIZONS = [1, 3, 5, 10]
TRAIN_RATIO = 0.70
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
            f"В файле отсутствуют столбцы: {missing}"
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
    return df
def prepare_data(df):
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
    df["call_signal"] = (
        (df["EMA20"] > df["EMA50"])
        & (df["RSI14"] >= 50)
        & (df["RSI14"] <= 65)
    )
    return df
def run_call_backtest(df, horizon):
    trades = []
    next_available_entry = 0
    previous_call_signal = False
    for i in range(len(df) - horizon):
        call_signal = bool(df.at[i, "call_signal"])
        # Берём только первый сигнал новой серии CALL.
        is_new_signal = call_signal and not previous_call_signal
        previous_call_signal = call_signal
        if not is_new_signal:
            continue
        entry_index = i + 1
        exit_index = entry_index + horizon - 1
        if entry_index < next_available_entry:
            continue
        if exit_index >= len(df):
            continue
        entry_price = float(df.at[entry_index, "open"])
        exit_price = float(df.at[exit_index, "close"])
        if entry_price <= 0:
            continue
        if abs(exit_price - entry_price) < 1e-12:
            outcome = "DRAW"
            profit = 0.0
        elif exit_price > entry_price:
            outcome = "WIN"
            profit = PAYOUT
        else:
            outcome = "LOSS"
            profit = -1.0
        trades.append({
            "signal_time": df.at[i, "datetime"],
            "entry_time": df.at[entry_index, "datetime"],
            "exit_time": df.at[exit_index, "datetime"],
            "entry_price": entry_price,
            "exit_price": exit_price,
            "outcome": outcome,
            "profit_units": profit
        })
        next_available_entry = exit_index + 1
    return pd.DataFrame(trades)
def report(trades, label, horizon):
    if trades.empty:
        print(f"{label} | {horizon}m: сделок нет")
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
        f"{label} | {horizon}m | "
        f"сделок {len(trades)} | "
        f"W/L/D {wins}/{losses}/{draws} | "
        f"победы {win_rate:.2f}% | "
        f"результат {profit:.2f}"
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
    df = prepare_data(load_data())
    split_index = int(len(df) * TRAIN_RATIO)
    early = df.iloc[:split_index].copy().reset_index(drop=True)
    holdout = df.iloc[split_index:].copy().reset_index(drop=True)
    print("=" * 70)
    print("HYDRA AI TRADER — CALL TEMPORAL SPLIT TEST")
    print("=" * 70)
    print("Всего свечей:", len(df))
    print(
        "Ранняя часть:",
        early["datetime"].iloc[0],
        "—",
        early["datetime"].iloc[-1],
        "| свечей:",
        len(early)
    )
    print(
        "Поздняя часть:",
        holdout["datetime"].iloc[0],
        "—",
        holdout["datetime"].iloc[-1],
        "| свечей:",
        len(holdout)
    )
    print("Выплата:", f"{PAYOUT:.0%}")
    print("Точка безубыточности без ничьих: 55.56%")
    print()
    results = []
    for horizon in HORIZONS:
        print("-" * 70)
        early_trades = run_call_backtest(early, horizon)
        holdout_trades = run_call_backtest(holdout, horizon)
        results.append(report(early_trades, "EARLY", horizon))
        results.append(report(holdout_trades, "HOLDOUT", horizon))
        if not early_trades.empty:
            early_trades.to_csv(
                f"backtest_call_early_{horizon}min.csv",
                index=False
            )
        if not holdout_trades.empty:
            holdout_trades.to_csv(
                f"backtest_call_holdout_{horizon}min.csv",
                index=False
            )
    result_df = pd.DataFrame(results)
    result_df.to_csv(
        "backtest_call_split_summary.csv",
        index=False
    )
    print()
    print("=" * 70)
    print("СВОДНАЯ ТАБЛИЦА")
    print(result_df.to_string(index=False))
    print()
    print("Сохранено: backtest_call_split_summary.csv")
    print("=" * 70)
if __name__ == "__main__":
    main()