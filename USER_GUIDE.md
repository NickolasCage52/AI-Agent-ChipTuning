# Parts Assistant — Руководство пользователя

## 1. Что это за бот

Parts Assistant — Telegram-бот для подбора автозапчастей. Заменяет ручной поиск по прайсам: принимает запрос, уточняет детали (не больше 2 вопросов), возвращает 3 варианта (Эконом / Оптимум / OEM) с ценами, сроками доставки и наличием.

**Примеры запросов:**
- «Нужны передние колодки на Toyota Camry 2016»
- «Масляный фильтр Kia Rio 2017»
- «Комплект ГРМ, подберите аналоги»
- «Артикул 04465-33480, что быстрее привезут»

---

## 2. Быстрый старт

### Запуск через Docker (рекомендуется)

```bash
# 1. Клонировать репозиторий
git clone <repo_url>
cd Ai_agent_chiptuning

# 2. Скопировать и настроить .env
cp .env.example .env
# Открыть .env и заполнить GEMINI_API_KEY

# 3. Запустить
docker compose up -d

# 4. Открыть в браузере
# http://localhost:3001  (по умолчанию порт 3001 — если 3000 занят)
```

### Запуск без Docker (если нужно)

```bash
# Backend (Python)
cd services/core-api
pip install -r requirements.txt
# Установить GEMINI_API_KEY в окружении
uvicorn app.main:app --reload --port 8000

# Frontend (TypeScript/Node)
cd apps/ui
npm install
npm run dev
```

## 3. Настройка .env

| Переменная | Описание | Где взять |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота | @BotFather в Telegram: /newbot |
| `GEMINI_API_KEY` | Ключ Gemini API | https://aistudio.google.com/app/apikey |
| `GEMINI_MODEL` | Модель | `gemini-2.0-flash` |
| `DATABASE_URL` | БД | `postgresql://user:pass@localhost/autoshop` |
| `ASYNC_DATABASE_URL` | Async БД | `postgresql+asyncpg://user:pass@localhost/autoshop` |
| `LOG_LEVEL` | Уровень логов | `INFO` |

## 4. Загрузка и обновление базы/прайсов

```bash
# Загрузить demo-данные (автоматически при первом запуске)
make seed

# Импорт прайса через API
curl -X POST -F "file=@demo-data/suppliers/demo.csv" -F "supplier_id=<uuid>" \
  http://localhost:8000/api/suppliers/import
```

Формат CSV прайса (разделитель `;` или `,`, заголовок — русский или английский):
```
Артикул;OEM;Наименование;Бренд;Цена;Наличие;Срок
PAD-001;04465-33480;Колодки тормозные передние Camry;AKEBONO;4200;6;2
```
Алиасы столбцов: sku/артикул, oem/OE/оригинал, name/наименование, brand/бренд, price/цена, stock/наличие, delivery_days/срок.

## 5. Каталог авто: выбор марки, модели, года, двигателя

### Что это
Выпадающие списки для выбора автомобиля. Каждый следующий список зависит от предыдущего выбора.

### Где хранятся данные
Каталог хранится в БД проекта (таблицы `vehicle_makes`, `vehicle_models`, `vehicle_engines`).

### Загрузка демо-данных
```bash
# Через Docker (рекомендуется)
docker compose run --rm -v "${PWD}/scripts:/scripts" -v "${PWD}/demo-data:/demo-data" core-api python /scripts/import_vehicle_catalog.py --file /demo-data/vehicle_catalog.csv

# Локально (из корня проекта, с запущенной БД)
python scripts/import_vehicle_catalog.py
```

### Загрузка своего каталога
```bash
python scripts/import_vehicle_catalog.py --file /path/to/your_catalog.csv
```

Формат CSV (заголовок обязателен):
```
make,make_slug,model,model_slug,year_from,year_to,engine_name,engine_code,displacement,fuel,power_hp,engine_year_from,engine_year_to
Toyota,toyota,Camry,camry,2011,2018,2.5 бензин (2AR-FE),2AR-FE,2.5,petrol,181,2011,2018
```

### Очистить и перезагрузить
```bash
python scripts/import_vehicle_catalog.py --clear --file /path/to/catalog.csv
```

### Как проверить, что UI видит марки
```bash
curl http://localhost:8000/api/vehicle/makes
# Должен вернуть JSON со списком марок
```

### Частые ошибки

| Проблема | Причина | Решение |
|---|---|---|
| Список марок пустой | Каталог не загружен | Запустить импорт (см. выше) |
| Ошибка кодировки при импорте | CSV сохранён не в UTF-8 | Пересохранить CSV в UTF-8 (в Excel: «Сохранить как» → CSV UTF-8) |
| "Catalog not loaded" в API | Пустая БД | Запустить импорт |
| После docker-compose up каталог пустой | Volume не сохранился | Проверить `docker volume ls`, переимпортировать |
| Модели не подгружаются | Неверный make_id | Проверить через `curl /api/vehicle/makes` реальные ID |

## 6. Telegram Bot — поиск только по прайсам

Бот подбирает запчасти **только из двух файлов прайса** (базовый + некондиция). Возвращает 3 варианта: Эконом / Оптимум / OEM.

**LLM:** Ollama (локально, primary) → Gemini (fallback). Рекомендуемые модели: `qwen2.5:7b`, `gemma2:9b`.

**Стартовое меню:** Полное ТО / Подбор по описанию / Есть артикул / Есть OEM / Есть VIN / Помощь.

**Команды:** `/start`, `/help`, `/reset`, `/debug` (для ADMIN_TG_ID).

### Куда загрузить прайсы

**Положите файлы в папку `data/price_sources/`:**
- `data/price_sources/base.csv` или `base.xlsx` — основной прайс
- `data/price_sources/defect.csv` или `defect.xlsx` — некондиция

Поддерживаемые колонки: `Номенклатура`, `Бренд`, `Артикул`, `Описание`, `Цена, руб.`, `Срок поставки, дн.`, `Наличие`, `Каталожный номер`, `OEM Номер` (или `OEМ Номер`).

Пример CSV (разделитель `;`):
```
Артикул;OEM;Наименование;Бренд;Цена;Наличие;Срок
PAD-001;04465-33480;Колодки тормозные передние Camry;AKEBONO;4200;6;2
```

### Импорт прайсов (запускать при каждой замене файлов)

```bash
python -m scripts.import_prices
# Или явно указать пути:
python -m scripts.import_prices --base data/price_sources/base.csv --defect data/price_sources/defect.csv
# В Docker (пересобрать образ: docker compose build telegram_bot):
docker compose run --rm -w /app -v "${PWD}/data:/app/data" telegram_bot python -m scripts.import_prices
```

Данные загружаются в SQLite: `data/parts.db`.

### Как пользоваться ботом

1. Найдите бота в Telegram
2. Нажмите /start — появится меню с кнопками сценариев
3. Выберите сценарий или напишите запрос свободно: «Нужны колодки на Camry 50», «OEM 90915-YZZF2», «Артикул BP02031»
4. Ответьте на 1–2 уточняющих вопроса (если будут)
5. Получите 3 тира (Эконом / Оптимум / OEM) — выберите кнопкой
6. Оцените подбор: 👍 Подошло / 👎 Не подошло

**Команды:** `/start`, `/help`, `/reset`, `/debug` (админ)

### Как оценить ответ бота

После каждого подбора бот спрашивает: «Как вам этот подбор?»

**👍 Подошло** — если нашли то что нужно. Затем можно уточнить что именно понравилось.
После лайка бот предложит начать новый поиск.

**👎 Не подошло** — если результат не устроил.
Бот попросит выбрать причину и написать комментарий — это помогает улучшить систему.
После дизлайка можно скорректировать запрос.

Если за 3 попытки не удалось найти нужное — бот сам предложит оценить и помочь.

### Запуск бота

**Docker:**
```bash
cp .env.example .env   # заполнить TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
python -m scripts.import_prices   # загрузить прайсы
docker compose up -d telegram_bot
```

**Без Docker:**
```bash
pip install -r requirements-telegram-bot.txt
cp .env.example .env
python -m scripts.import_prices
python -m apps.telegram_bot.bot
```

### Устранение проблем (прайсы)

| Проблема | Решение |
|---|---|
| Бот не отвечает | Проверить TELEGRAM_BOT_TOKEN: `curl https://api.telegram.org/bot{TOKEN}/getMe` |
| Пустые результаты | Запустить `python -m scripts.import_prices`, проверить `data/parts.db` |
| Ошибка импорта XLSX | `pip install openpyxl` |
| Кодировка CSV | Сохранить в UTF-8 или CP1251 |
| Gemini не отвечает | Проверить GEMINI_API_KEY, лимиты на aistudio.google.com |
| Ollama не работает | Запустить `ollama run qwen2.5:7b`, проверить OLLAMA_BASE_URL |
| В Docker прайсы пустые | Проверить volume `./data:/app/data`, переимпортировать |

## 7. Типовые сценарии использования

### Подбор запчасти

1. Заполните плашку: Марка → Модель → Год (обязательно).
2. Напишите в чате: «Нужны передние тормозные колодки».
3. Ответьте на уточняющие вопросы (не более 2).
4. Выберите тир: Эконом / Оптимум / OEM.
5. Нажмите «Выбрать» для фиксации.

### Подбор по артикулу

1. Напишите: «Артикул 04465-33480».
2. Ассистент покажет варианты и сроки доставки.

### Подбор ТО

1. Заполните пробег в плашке.
2. Нажмите чип «ТО» или напишите «Нужно ТО».
3. Ассистент подберёт комплект расходников.

## 8. Частые ошибки и диагностика

| Проблема | Решение |
|---|---|
| «Не удалось подключиться к ИИ» | Проверить GEMINI_API_KEY в .env, перезапустить docker-compose |
| Ассистент не находит запчасти | Проверить загрузку прайсов: `make seed`, импорт CSV |
| Пустой экран / нет ответа | Открыть DevTools (F12) → Console, сообщить об ошибке |
| Контейнер не стартует | `docker compose logs` для просмотра ошибок |
| Порт 3000 занят | `$env:UI_PORT='3001'; docker compose up -d` — тогда UI на http://localhost:3001 |
| Бот не отвечает | Неверный TELEGRAM_BOT_TOKEN | Проверить токен через curl «https://api.telegram.org/bot{TOKEN}/getMe» |
| «Не смог обработать» | Ошибка Gemini API | Проверить GEMINI_API_KEY, лимиты |
| Пустые варианты | Каталог не загружен | `make seed`, импорт прайса |
| Бот завис на уточнении | Бесконечный цикл | Написать /reset |
| Контейнер telegram_bot не стартует | Ошибка .env | `docker compose logs telegram_bot` |

Просмотр логов бота:
```bash
docker compose logs -f telegram_bot
```

## 9. Бэкап и обновление

```bash
# Бэкап БД (PostgreSQL)
docker compose exec postgres pg_dump -U autoshop autoshop > backup_$(date +%Y%m%d).sql

# Обновление приложения
git pull
docker compose build
docker compose up -d
```

## 10. Smoke-тест

```bash
# Запустить проект
docker compose up -d

# Прогнать 4 сценария
python scripts/smoke_test.py
```
