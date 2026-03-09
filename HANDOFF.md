# Estate Invest — Handoff (обновлено: 2026-03-05, сессия 3)

## Что это
Передаточный документ между сессиями. Содержит полный контекст для продолжения работы.

---

## Текущий статус: Python-монитор торгов — РАБОТАЕТ на VPS

### Что сделано (хронология)
1. **Сессия 1**: Исследование (80+ источников), VPS, n8n workflow MVP
2. **Сессия 2**: Python-монитор (`torgi_monitor.py`) заменил n8n, Google Sheets интеграция, улучшенные фильтры аналогов, ЕФРСБ мониторинг
3. **Сессия 3**: HTML-презентация AI-аналитики для партнёров, архитектура PropertyCard (план)

### Архитектура (текущая)
```
Cron (каждые 4 часа)
        ↓
torgi_monitor.py на VPS → torgi.gov.ru API (catCodes: 2,3,4,5,7,8,10,11,47)
        ↓
parse_lot() → extract_land_type() / extract_commercial_type() / extract_district()
        ↓
fetch_analogs() → ads-api.ru (3-уровневый фаллбек: точный → мягкий → базовый)
        ↓
evaluate_market_price() → медиана цены за м2/сотку
        ↓
send_telegram() → @topparsing канал + Google Sheets запись
```

```
efrsb_monitor.py на VPS → fedresurs.ru API (curl, Qrator bypass)
        ↓
Telegram уведомления о банкротных торгах
```

---

## Инфраструктура

### VPS (Timeweb Cloud, Москва)
- IP: `5.42.102.36`
- SSH: `ssh root@5.42.102.36` / пароль: `sp8hWiGY+kHsN6`
- ОС: Ubuntu 24.04, тариф: 350 руб/мес
- Код: `/opt/torgi-proxy/`
  - `torgi_monitor.py` — основной монитор торгов (~710 строк)
  - `efrsb_monitor.py` — мониторинг ЕФРСБ
  - `main.py` — FastAPI прокси (legacy, для n8n)
  - `google-sa.json` — service account для Google Sheets
  - `seen_lots.json` — дедупликация torgi.gov.ru
  - `seen_efrsb.json` — дедупликация ЕФРСБ
- Cron: `0 */4 * * *` для обоих скриптов
- Systemd: `torgi-proxy.service` (FastAPI прокси на 8080)

### n8n Cloud
- URL: `https://estateinvest.app.n8n.cloud`
- Workflow PROD: `H12Q90yhl9q1MNiI` (ACTIVE, но заменён Python-скриптом)
- Workflow DEV: `RXbhtdi37u50TYQf`
- **TODO**: деактивировать n8n PROD после проверки стабильности Python

### Telegram
- Бот мониторинга: @monitor_estate_bot (`8650381430:AAFKGNZbjQmhAd3ogse9gOWs7_2xoypuo-A`)
- Канал: @topparsing "Лоты по Перми" (chat_id: `-1003759471621`)
- Chat ID Ярослав: `191260933`
- Бот техн. уведомлений: `8604957943:AAF37XNjilxzwZV39MMTeGvVAalr95UrSpo`

### Google Sheets
- Таблица: `1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk` "Монитор торгов — Лоты"
- Лист: "Лоты", 21 колонка (lotId...analogsCount)
- Service Account: `google-sa.json` на VPS

### GitHub
- Приватный: `yarbalakin/estate-invest` (основной код)
- Публичный: `yarbalakin/estate-invest-academy` (GitHub Pages)
  - URL: `https://yarbalakin.github.io/estate-invest-academy/`
  - Файлы: `index.html`, `реализация-сводка.html`, `ai-analytics.html`

---

## Ключевые файлы

| Файл | Что |
|------|-----|
| `HANDOFF.md` | Этот файл |
| `Аналитика/torgi_monitor.py` | Основной Python-монитор (~710 строк) |
| `Аналитика/RESEARCH.md` | Исследование (550 строк) |
| `Аналитика/research.html` | Визуальная версия исследования |
| `Аналитика/ai-analytics-для-партнёров.html` | Презентация для партнёров (тултипы, Q&A) |
| `estate-invest-для-партнёров.html` | Презентация компании для партнёров |

---

## torgi_monitor.py — ключевые функции

- `parse_lot()` — парсинг лота, возвращает dict с landType, commercialType, lotName, lotDesc
- `extract_land_type(name, desc)` — определяет ИЖС/СНТ/промка из текста
- `extract_commercial_type(name, desc)` — определяет офис/торговое/склад/производство
- `extract_district(address)` — извлекает район из адреса
- `fetch_analogs()` — 3-уровневый фаллбек поиска аналогов на ads-api.ru
- `evaluate_market_price()` — медиана цены за м2/сотку
- `append_google_sheets()` — запись лота в Google Sheets
- `ADS_AREA_PARAMS` — маппинг серверных фильтров площади по категориям

---

## Архитектура PropertyCard (СПЛАНИРОВАНА, НЕ РЕАЛИЗОВАНА)

Полный план: `.claude/plans/enchanted-wandering-swan.md`

Суть: для каждого лота создаём полный профиль из нескольких источников (torgi, кадастр, ads-api), для аналогов тоже. Сравниваем профили по 5 параметрам (площадь 25%, расстояние 25%, назначение 20%, кадастр 15%, тип 15%). Взвешенная оценка вместо медианы.

### Фазы реализации
1. **PropertyCard + Кадастр** (2 нед) — модуль property_card.py, PKK Росреестр API, SQLite
2. **Скоринг похожести** (2 нед) — 5-параметрический scoring, взвешенная оценка
3. **ML + расширение** (1-2 мес) — XGBoost, SHAP, расширение регионов

---

## Следующие шаги (приоритет)

### Сейчас
- [ ] Деактивировать n8n PROD workflow (Python-скрипт его заменил)
- [ ] Реализовать PropertyCard (Фаза 1): property_card.py + cadastral.py + SQLite

### Далее
- [ ] Скоринг похожести (Фаза 2)
- [ ] ML-модель XGBoost (Фаза 3, когда 500+ объектов в базе)
- [ ] Доходный подход для коммерции (аренда → капитализация)

---

## Известные проблемы
- torgi.gov.ru недоступен из EU — нужен российский IP (VPS)
- asocks прокси блокирует .gov.ru — не использовать
- fedresurs.ru: Python requests блокируется Qrator, curl работает
- ads-api.ru: тестовый тариф отдаёт price=0, нужен платный (2000 руб/мес)
- n8n cloud: лимит 5 concurrent executions, webhook только на новых workflows
