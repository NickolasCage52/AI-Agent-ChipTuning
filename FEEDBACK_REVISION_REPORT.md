# ╔══════════════════════════════════════════════════════╗
# ║           ОТЧЁТ РЕВИЗИИ: FEEDBACK LOOP               ║
# ╚══════════════════════════════════════════════════════╝
# Дата: 2025-03-09
# Проект: Ai_agent_chiptuning — Telegram-бот автоподборщик запчастей

---

## TELEGRAM FLOW

| Элемент | Реализация |
|---------|------------|
| **Где начинается цикл диалога** | `apps/telegram_bot/handlers/messages.py` — `handle_message()` (строка 31). Вход: любой текст от пользователя. Контекст берётся из `state.get_data()`. |
| **Где определяется финальный ответ** | `apps/telegram_bot/handlers/messages.py`, строки 136–195. После `search()` → `build_tiers()` → `format_results()` отправляется `message.answer(response_text, reply_markup=results_keyboard())`. |
| **Где хранится контекст** | **MemoryStorage + SQLite**. `apps/telegram_bot/storage.py` — `SQLiteStorage`, таблица `fsm_storage` в `data/parts.db`. Ключ: `bot_id:chat_id:user_id`. |
| **FSM-состояния** | `apps/telegram_bot/states.py`: `PartsSearch` — `idle`, `waiting_clarification`, `showing_results`. |

---

## LLM

| Элемент | Реализация |
|---------|------------|
| **Где system prompt** | `core/intent.py`, строки 19–67 — константа `SYSTEM_PROMPT`. |
| **Содержимое промпта** | Инструкция для извлечения intent и слотов (JSON). Синонимы запчастей, марки авто, правила для general_question. Ответ — только JSON. |
| **Модель** | **Ollama** (primary): `qwen2.5:7b` через `llm/ollama_client.py`. **Gemini** (fallback): `gemini-2.0-flash` через `core/llm_adapter.py`. Роутер: `llm/router.py`. |
| **Fallback** | Да. `llm/router.py`: при ошибке Ollama → `call_gemini()`. В `core/intent.py`: при недоступности LLM — `_fallback_extract()` (rule-based). |
| **Дополнительный system prompt** | `GENERAL_QUESTION_SYSTEM` в `apps/telegram_bot/handlers/messages.py:14–17` — для общих вопросов (эксперт-автомеханик). |

---

## ХРАНИЛИЩЕ

| Элемент | Реализация |
|---------|------------|
| **БД** | `data/parts.db` (SQLite). Путь задаётся через `DB_PATH` в `core/logger.py` и `apps/telegram_bot/storage.py`. |
| **Таблицы** | `fsm_storage` (FSM), `debug_logs` (события), `products`, `products_defect`, `import_runs` — последние три от `scripts/import_prices.py`. |
| **Логи в БД** | Да. `core/logger.py` — `log_event_to_db()` пишет в `debug_logs` (event_type, tg_user_id, payload_json, llm_backend, latency_ms). |
| **История диалогов** | Частично. Сообщения хранятся в FSM data (`clarification_answers`, `last_tiers`, `original_query`), но отдельной таблицы диалогов нет. |

---

## FEEDBACK

| Элемент | Реализация |
|---------|------------|
| **Уже реализован** | **Нет.** |
| **Что переиспользовать** | `log_event_to_db()` — расширить payload для `offers_shown`/`option_selected`. `core/pii_masker` — маскирование перед сохранением. `SQLiteStorage` — паттерн работы с `parts.db`. Структура `results_keyboard()` — добавить feedback-кнопки в отдельный блок после тиров. |
| **Что добавить с нуля** | Таблицы `dialogue_cycles`, `feedback`, `prompt_versions`, `overlay_changes`, `feedback_archive`. Обработчики callback `feedback_like`, `feedback_dislike`, `like_cat_*`, `dislike_reason_*`. FSM-состояния `waiting_feedback`, `waiting_dislike_reason`, `waiting_dislike_comment`, `waiting_like_category`. Логика счётчика `attempt_count` и триггер оценки при ≥3. |

---

## PROMPT VERSIONING

| Элемент | Реализация |
|---------|------------|
| **Есть** | **Нет.** |
| **Где хранятся версии** | Отсутствует. `SYSTEM_PROMPT` — константа в коде. |
| **Что добавить** | `config/prompt_core.txt` — вынести неизменяемое ядро. `config/prompt_overlay.yaml` — изменяемый слой. `llm/prompt_manager.py` — объединение core + overlay, версионирование. Таблица `prompt_versions` в БД. |

---

## СТРУКТУРА ПРОЕКТА (релевантные файлы)

```
apps/telegram_bot/
  bot.py                 # точка входа, диспетчер
  handlers/
    commands.py          # /start, /reset
    messages.py          # handle_message — основной цикл
    callbacks.py         # tier_*, scenario_*, reset
  storage.py             # SQLiteStorage для FSM
  session.py             # заглушки load/save
  states.py              # PartsSearch
  menus.py               # клавиатуры
  formatter.py           # format_results, format_clarification

core/
  intent.py              # SYSTEM_PROMPT, extract_intent_and_slots
  price_search.py       # search, build_tiers
  logger.py             # log_event, log_event_to_db
  llm_adapter.py         # call_gemini
  pii_masker.py          # mask_pii
  maintenance_logic.py

llm/
  router.py              # generate: Ollama → Gemini
  ollama_client.py       # Ollama API

config/
  maintenance_config.yaml

data/
  parts.db               # fsm_storage, debug_logs, products, ...
```

---

## ВЫВОДЫ ДЛЯ ВНЕДРЕНИЯ

1. **Точка внедрения feedback-кнопок:** сразу после `message.answer(response_text, ...)` в `messages.py:195` — вызывать `show_feedback_request()`. Либо изменить `results_keyboard()` чтобы включить 👍/👎, но по ТЗ — отдельный блок «Как вам подбор?».

2. **Разделение core/overlay:** вынести `SYSTEM_PROMPT` из `intent.py` в `config/prompt_core.txt`, синонимы и примеры — в `config/prompt_overlay.yaml`.

3. **Новые таблицы:** создавать в том же `parts.db` через миграционный скрипт или при старте.

4. **Путь к storage:** в ТЗ указан `storage/feedback_repository.py`, в проекте нет папки `storage/`. Создать `storage/` в корне или использовать `core/` — на усмотрение. Рекомендация: `storage/` в корне для разделения ответственности.

5. **Путь telegram_adapter:** в ТЗ — `telegram_adapter/handlers/`. Фактически — `apps/telegram_bot/handlers/`. Использовать `apps/telegram_bot/`.

6. **Счётчик attempt_count:** хранить в FSM data или в `dialogue_cycles`. При каждом показе тиров без выбора tier — инкремент. Логика в `messages.py` при переходе в `showing_results` и в `callbacks.py` при выборе tier.

---

## DEFINITION OF DONE — ЧЕКЛИСТ

- [ ] После каждого финального подбора — кнопки 👍/👎
- [ ] После 3 неудачных попыток — автоматический запрос оценки
- [ ] Сценарии 👍 и 👎 с сохранением в feedback
- [ ] Таблицы `dialogue_cycles`, `feedback`, `prompt_versions`, `overlay_changes`
- [ ] `PromptManager` + core/overlay
- [ ] `core/intent.py` использует `PromptManager.get_active_prompt()`
- [ ] `config/prompt_overlay.yaml`, `config/prompt_core.txt`
- [ ] `SAFE_MUTATION_KEYS` / `PROTECTED_KEYS`
- [ ] `apply_prompt_version.py`, `generate_reports.py`, `analyze_feedback.py`, `cleanup_old_feedback.py`
- [ ] PII анонимизация (sha256 от tg_user_id)
- [ ] SQL views, CSV export, архивация
- [ ] Обновление USER_GUIDE.md, ADMIN_GUIDE.md, README.md

---

══════════════════════════════════════════════════════
