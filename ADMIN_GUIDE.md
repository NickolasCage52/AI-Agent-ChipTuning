# ADMIN_GUIDE — Администрирование Parts Assistant

## Feedback система

### Таблицы БД

| Таблица | Описание |
|--------|----------|
| `dialogue_cycles` | Полный цикл диалога: запрос → уточнения → подбор |
| `feedback` | Оценки пользователей (👍/👎) с причинами и комментариями |
| `prompt_versions` | Версии промптов (core + overlay) |
| `overlay_changes` | История изменений adaptive layer |
| `feedback_archive` | Архив старых записей (старше 90 дней) |

### Команды

```bash
# Отчёт за 30 дней
python -m scripts.generate_reports --days 30

# Экспорт CSV
python -m scripts.generate_reports --export-csv --output reports/

# Анализ и рекомендации
python -m scripts.analyze_feedback --suggest-synonyms
python -m scripts.analyze_feedback --suggest-prompt-improvements

# Применить новую версию промпта
python -m scripts.apply_prompt_version --reason "Добавлены синонимы"

# Откатить версию
python -m scripts.apply_prompt_version --rollback 1.0.0

# Архивировать старые данные
python -m scripts.cleanup_old_feedback
```

### Включение/выключение автоулучшения

В `.env`:
```
AUTO_IMPROVE=true   # включено (осторожно)
AUTO_IMPROVE=false  # выключено (рекомендуется по умолчанию)
```

### Интерпретация метрик

| Метрика | Действие |
|---------|----------|
| success_rate < 70% | Нужно улучшать промпт или поиск |
| Частая причина «wrong_understanding» | Добавить синонимы в `config/prompt_overlay.yaml` |
| Частая причина «wrong_parts» | Улучшить поиск по БД |
| attempt_count > 2 часто | Упростить диалоговую логику |

### Как использовать хорошие кейсы

```bash
python -m scripts.analyze_feedback --good-cases
```

Добавить лучшие примеры в `config/prompt_overlay.yaml` → `few_shot_examples`.

### Как использовать плохие кейсы

```bash
python -m scripts.analyze_feedback --bad-cases
```

Разобрать причины → исправить синонимы / поиск / промпт вручную.
