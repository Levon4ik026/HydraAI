import pandas as pd

FILE_NAME = "eurusd_history.csv"

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

    relative_strength = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + relative_strength))

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0),
        100
    )

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain == 0),
        50
    )

    return rsi

def main():
    print("=" * 45)
    print("       HYDRA AI TRADER")
    print("       ANALYSIS MODULE")
    print("=" * 45)

    try:
        df = pd.read_csv(FILE_NAME)
    except FileNotFoundError:
        print("ERROR: File eurusd_history.csv not found.")
        return

    required_columns = ["datetime", "open", "high", "low", "close"]

    if not all(column in df.columns for column in required_columns):
        print("ERROR: CSV file has an incorrect structure.")
        return

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    df = df.dropna(subset=required_columns)
    df = df.sort_values("datetime").reset_index(drop=True)

    if len(df) < 60:
        print("ERROR: Not enough candles for analysis.")
        return

    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    df["RSI14"] = calculate_rsi(df["close"], 14)

    last = df.iloc[-1]

    print()
    print("Instrument: EUR/USD")
    print("Candles loaded:", len(df))
    print("Last candle:", last["datetime"])
    print("Last close:", round(last["close"], 5))
    print("EMA 20:", round(last["EMA20"], 5))
    print("EMA 50:", round(last["EMA50"], 5))
    print("RSI 14:", round(last["RSI14"], 2))

    print()
    print("PRELIMINARY MARKET ASSESSMENT")

    if last["EMA20"] > last["EMA50"]:
        print("Trend: upward")
    elif last["EMA20"] < last["EMA50"]:
        print("Trend: downward")
    else:
        print("Trend: neutral")

    if last["RSI14"] >= 70:
        print("RSI: potentially overbought")
    elif last["RSI14"] <= 30:
        print("RSI: potentially oversold")
    else:
        print("RSI: middle range")

    print()
    print("Trading signal: WAIT")
    print("This module only calculates indicators.")
    print("It does not confirm a profitable trade.")
    print("=" * 45)

if __name__ == "__main__":
    main()





