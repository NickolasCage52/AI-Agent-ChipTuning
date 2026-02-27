#!/usr/bin/env python3
"""Диагностика подключения к Gemini API."""

import os

# Загружаем .env если есть
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

print(f"API Key loaded: {'YES' if api_key else 'NO - KEY IS MISSING!'}")
if api_key:
    print(f"Key prefix: {api_key[:8]}...")
print(f"Model: {model}")

if not api_key:
    print("Set GEMINI_API_KEY in .env and run again.")
    exit(1)

try:
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents="Скажи 'OK' и ничего больше.")
    text = response.text if hasattr(response, "text") else str(response)
    print(f"Gemini ответил: {text}")
    print("OK")
except Exception as e:
    err_msg = str(e)
    print(f"Ошибка Gemini: {type(e).__name__}: {err_msg}")
    if "location" in err_msg.lower() or "not supported" in err_msg.lower():
        print("\n--- Регион не поддерживается ---")
        print("Gemini API недоступен в вашем регионе. Варианты:")
        print("1. Включить VPN (страна: US, UK, и т.п.)")
        print("2. Запустить backend на сервере в поддерживаемом регионе (EU/US)")
        print("3. Использовать Vertex AI вместо Gemini Developer API")
    exit(1)
