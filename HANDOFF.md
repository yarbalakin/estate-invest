# Estate Invest — Handoff (обновлено: 2026-03-04, сессия 1)

## Что это
Передаточный документ между сессиями. Содержит полный контекст для продолжения работы.

---

## Текущий статус: MVP v0 "Монитор торгов Пермь" — РАБОТАЕТ

### Что сделано
- Исследование (8 отчётов, 80+ источников) → `Аналитика/RESEARCH.md`
- VPS в Москве для проксирования torgi.gov.ru (недоступен из EU)
- n8n workflow: парсинг торгов → дедупликация → Telegram уведомления
- Первый тест прошёл успешно — лоты приходят в Telegram

### Архитектура
```
Schedule (4ч) / Webhook GET
        ↓
n8n HTTP Request → VPS (FastAPI прокси) → torgi.gov.ru JSON API
        ↓
Code нода (парсинг + дедупликация через staticData)
        ↓
HTTP Request → Telegram Bot API → чат Ярослава
```

---

## Инфраструктура

### n8n Cloud
- URL: `https://estateinvest.app.n8n.cloud`
- Workflow ID: `H12Q90yhl9q1MNiI`
- Workflow name: "Монитор торгов Пермь — MVP v0"
- Статус: **ACTIVE**
- Webhook: `GET https://estateinvest.app.n8n.cloud/webhook/torgi-monitor-v0`

### VPS (Timeweb Cloud, Москва)
- IP: `5.42.102.36`
- SSH: `ssh root@5.42.102.36` / пароль: `sp8hWiGY+kHsN6`
- IPv6: `2a03:6f00:a::1:9551`
- ОС: Ubuntu 24.04
- Тариф: Cloud MSK 15 (350 руб/мес)
- Сервис: FastAPI прокси на порту 8080
  - Health: `http://5.42.102.36:8080/health`
  - API: `http://5.42.102.36:8080/api/torgi?catCode=2&dynSubjRF=59&size=100`
  - API Key (header): `X-API-Key: ei-torgi-2026-mvp`
  - Systemd: `torgi-proxy.service` (auto-restart)
  - Код: `/opt/torgi-proxy/main.py`
  - Venv: `/opt/torgi-proxy/venv/`

### Telegram
- Bot: @monitor_estate_bot "Мониторолог Estate Invest" (token: `8650381430:AAFKGNZbjQmhAd3ogse9gOWs7_2xoypuo-A`)
- Chat ID личный: `191260933` (Ярослав Балакин)
- Канал: `@topparsing` "Лоты по Перми" (chat_id: `-1003759471621`)
- Бот техн. уведомлений Claude Code: token `8604957943:AAF37XNjilxzwZV39MMTeGvVAalr95UrSpo`

### Прокси (asocks, НЕ РАБОТАЕТ для torgi.gov.ru)
- `https://...@62.112.8.229:443` — блокирует .gov.ru домены, не использовать

---

## torgi.gov.ru API

### Эндпоинт
```
GET https://torgi.gov.ru/new/api/public/lotcards/search
  ?catCode=2              # недвижимость
  &dynSubjRF=59           # Пермский край
  &size=100&page=0
  &sort=firstVersionPublicationDate,desc
  &lotStatus=PUBLISHED,APPLICATIONS_SUBMISSION
```

### Особенности
- SSL: российский CA — недоступен из EU, нужен российский IP
- Rate limit: ~60-120 req/min, пауза 1-3 сек достаточно
- Макс 10 000 результатов (100 стр x 100)
- characteristics[] — сложная структура: значения бывают string, number, object, array
- Ключевые коды характеристик: `Square`, `SquareZU_project`, `TotalArea`, `CadastralNumber`, `Address`, `addressFIAS`
- Лицензия: Open Data, свободное коммерческое использование

---

## Известные проблемы

1. **Адрес парсится плохо** — приходит "Российская Федерация" вместо полного адреса. Нужно брать из `lotDescription` или из вложенных характеристик
2. **Цена = 0** у некоторых лотов (земельные участки без начальной цены)
3. **n8n cloud: webhook не регистрируется** при добавлении к существующему workflow — нужно создавать workflow сразу с webhook
4. **n8n cloud: Telegram ноды** — работают (через webhook), НЕ через встроенный Telegram Trigger
5. **asocks прокси** — блокирует .gov.ru, не использовать

---

## Следующие шаги (приоритет)

### Итерация 1.1 — Улучшение парсинга
- [ ] Исправить парсинг адреса (lotDescription / карточка лота)
- [ ] Фильтр: только жильё + банкротство (убрать землю сельхоз)
- [ ] Добавить Google Sheets для хранения лотов
- [ ] Улучшить формат Telegram-сообщения

### Итерация 2 — Оценка (price gap)
- [ ] Подключить ads-api.ru (14 дней free) или cianparser
- [ ] Rule-based оценка: медиана цены за м2 аналогов
- [ ] Добавить в сообщение: рыночная цена, % скидки, confidence

### Итерация 3 — Масштабирование
- [ ] ЕФРСБ (банкротные торги)
- [ ] ML-модель (XGBoost/LightGBM)
- [ ] Веб-дашборд
- [ ] Переход на Python (когда n8n упрётся в потолок)

---

## Ключевые файлы проекта

| Файл | Что |
|------|-----|
| `HANDOFF.md` | Этот файл — передача контекста |
| `Аналитика/RESEARCH.md` | Полное исследование (550 строк) |
| `Аналитика/research.html` | Визуальная версия исследования |
| `ПЛАН_РЕАЛИЗАЦИИ.md` | План Streamlit-дашборда (5 блоков) |
| `company-profile.md` | Справочник компании (708 строк) |
| `CLAUDE.md` | Инструкции для AI |

---

## Параллельные проекты (не трогать)

- **Streamlit аналитика** (`Аналитика/`) — блоки 1-2 сделаны, блок 3 в процессе
- **Командная панель** (`командная панель/`) — 28 файлов исследования дизайна
- **Авито мониторинг** — несколько n8n workflows (СКАУТ, АНАЛИТИК, АРХИВАРИУС)
- **Денежный бот** — Telegram бот для учёта расходов (ACTIVE)
