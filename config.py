import os

# Храни ключ Twelve Data только в переменной окружения.
# Windows PowerShell: $env:TWELVE_DATA_API_KEY = "твой_новый_ключ"
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
