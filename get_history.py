import requests
import pandas as pd
from config import API_KEY
URL = "https://api.twelvedata.com/time_series"
params = {
    "symbol": "EUR/USD",
    "interval": "1min",
    "outputsize": 500,
    "apikey": API_KEY,
    "timezone": "UTC",
    "order": "asc"
}
print("HYDRA AI: zagruzka istorii EUR/USD...")
data = None
for attempt in range(1, 4):
    try:
        print(f"Попытка {attempt}/3...")
        response = requests.get(URL, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "values" in data:
            break
        print("API вернул ошибку:")
        print(data)
        break
    except requests.exceptions.Timeout:
        print("Превышено время ожидания ответа сервера.")
        if attempt == 3:
            print("Не удалось загрузить данные после 3 попыток.")
    except requests.exceptions.RequestException as error:
        print("Ошибка соединения:", error)
        break
if data is not None and "values" in data:
    df = pd.DataFrame(data["values"])
    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime", "open", "high", "low", "close"])
    df = df.sort_values("datetime")
    df = df.drop_duplicates(subset=["datetime"])
    if not df.empty:
        df.to_csv("eurusd_history.csv", index=False)
        print("\nSUCCESS! История сохранена.")
        print("Количество свечей:", len(df))
        print("Первая свеча:", df.iloc[0]["datetime"])
        print("Последняя свеча:", df.iloc[-1]["datetime"])
        print("\nПоследние 5 свечей:")
        print(df.tail(5).to_string(index=False))
    else:
        print("Полученные данные пустые или некорректные.")
        print("Существующий CSV не изменён.")
else:
    print("История не загружена. Существующий CSV не изменён.")