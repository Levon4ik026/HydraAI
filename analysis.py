import pandas as pd

import numpy as np

print("=" * 40)

print("HYDRA AI TRADER")

print("Проверка аналитического модуля")

print("=" * 40)

# Демонстрационные данные — не реальные котировки

np.random.seed(42)

price = 1.10000 + np.cumsum(

    np.random.normal(0, 0.0001, 100)

)

df = pd.DataFrame({"close": price})

# Скользящие средние

df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()

df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

# Изменение цены

df["change"] = df["close"].diff()

# RSI

gain = df["change"].clip(lower=0)

loss = -df["change"].clip(upper=0)

avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()

avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()

rs = avg_gain / avg_loss.replace(0, np.nan)

df["RSI"] = 100 - (100 / (1 + rs))

last = df.iloc[-1]

print(f"Последняя цена: {last['close']:.5f}")

print(f"EMA 20:         {last['EMA20']:.5f}")

print(f"EMA 50:         {last['EMA50']:.5f}")

print(f"RSI:            {last['RSI']:.2f}")

if last["EMA20"] > last["EMA50"]:

    print("Тренд: восходящий")

elif last["EMA20"] < last["EMA50"]:

    print("Тренд: нисходящий")

else:

    print("Тренд: неопределённый")

print("=" * 40)

print("Проверка завершена!")

print("Данные выше демонстрационные.")