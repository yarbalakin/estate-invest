# Исследование ЕФРСБ — парсинг банкротных торгов

> **ПРАВИЛО ДЛЯ АГЕНТОВ**: Прочитай этот файл ПОЛНОСТЬЮ перед началом работы.
> Не пробуй подходы помеченные ❌. Продолжай с текущего решения или пробуй из "Что ещё можно попробовать".
> После каждого эксперимента — ОБЯЗАТЕЛЬНО запиши результат сюда.

## Цель
Парсить торги недвижимости с fedresurs.ru (ЕФРСБ) → отправлять новые лоты в Telegram.

## API
- Список торгов: `GET https://fedresurs.ru/backend/biddings?searchByRegion=true&regionCode=59&limit=30&offset=0`
- Детали торга: `GET https://fedresurs.ru/backend/biddings/{guid}`
- Сообщение (лоты, цены): `GET https://fedresurs.ru/backend/bankruptcy-messages/{msg_guid}`
- Перед API-запросом нужно загрузить главную страницу для получения cookies Qrator (anti-DDoS)

## Защита сайта — Qrator
Qrator Labs — российский anti-DDoS сервис. На fedresurs.ru:
- Ставит cookie `qrator_ssid2` при первом визите
- Проверяет TLS fingerprint (JA3/JA4)
- Может блокировать с HTTP 451 если fingerprint не совпадает с реальным браузером

## Подходы (что пробовали)

### 1. Python requests (НЕ РАБОТАЕТ)
- `requests.get()` с сессией и headers
- **Результат**: HTTP 451 — Qrator блокирует по TLS fingerprint Python
- Python requests имеет характерный TLS fingerprint, отличный от браузера

### 2. Python requests + прокси (НЕ РАБОТАЕТ)
- Те же requests но через резидентный прокси (asocks.com)
- **Результат**: HTTP 451 — TLS fingerprint не зависит от прокси, блокируется так же

### 3. curl через subprocess — отдельные вызовы (НЕ РАБОТАЕТ)
- `subprocess.run(["curl", ...])` для каждого запроса
- **Результат**: 451 — каждый subprocess.run это новый процесс, у прокси `hold-session-session-$PID` разный PID = разный IP, cookies от init IP не валидны для API IP

### 4. curl inline bash (`bash -c "скрипт"`) (РАБОТАЕТ с прокси)
- Весь скрипт (init + API) в одном `subprocess.run(["bash", "-c", script])`
- Один PID → один IP → cookies валидны
- **Результат**: работает! Но медленно (прокси добавляет 5-15 сек на запрос)

### 5. Внешний .sh файл (`efrsb_fetch.sh`) (НЕ РАБОТАЕТ)
- Тот же код что в inline, но в .sh файле
- `bash /opt/torgi-proxy/efrsb_fetch.sh biddings 59`
- **Результат**: 0 байт на API-запросе, хотя init 200
- bash -x показывает что curl выполняется с правильными параметрами, но возвращает пустоту
- Причина не установлена точно. Возможно: другой PID при каждом запуске → другой IP прокси
- Inline bash сразу после → работает. 3 запуска .sh → все 0 байт

### 6. Прямое подключение с VPS + curl subprocess + tmpfile (РАБОТАЕТ — ТЕКУЩЕЕ РЕШЕНИЕ) ✅
- VPS в Москве (Timeweb Cloud, 5.42.102.36)
- fedresurs.ru доступен напрямую с российского IP, прокси НЕ НУЖЕН
- curl через `subprocess.run(["curl", ...])` с записью в tmpfile (stdout не работает!)
- **ВАЖНО**: `limit=30` → HTTP 451 (Qrator блокирует). `limit=15` → OK. Используем пагинацию.
- **ВАЖНО**: curl stdout через `capture_output=True` возвращает пустоту. Обязательно `-o tmpfile`.
- Init (загрузка главной) → sleep 5 → API запросы с cookies
- **Результат**: 14 торгов обработано, 15 сообщений в Telegram ✅
- Cron: `0 */4 * * *` на VPS
- Скрипт: `/opt/torgi-proxy/efrsb_monitor.py`

## Прокси (asocks.com)
- API: `https://api.asocks.com/v2/proxy/ports?apikey=KEY`
- Типы: `hold-query` (новый IP каждый запрос), `hold-session-session-TAG` (один IP на сессию)
- `hold-query` не подходит — cookies привязаны к IP
- `hold-session` работает но медленно (12+ сек на запрос)
- С VPS прокси не нужен

## Коды недвижимости (классификатор)
```
0101     — Здания
0101007  — Здания жилые многоквартирные
0101015  — Здания торговли
0101016  — Здания жилые
0101017  — Здания жилые индивидуальные
0103     — Сооружения
0108     — Земельные участки
0108001  — Земельные участки
0301     — Право аренды
```

## Статусы торгов (пропускаем)
- TradeCompleted — завершены
- TradeFailed — не состоялись
- TradeCancelled — отменены
- TradeAnnulled — аннулированы
- TradeSuspended — приостановлены

## Что ещё можно попробовать (если прямой доступ перестанет работать)
1. **curl-cffi / curl_cffi** — Python-библиотека с имитацией TLS fingerprint браузера (Chrome/Firefox)
2. **Playwright/Selenium** — headless браузер, полная имитация
3. **tls-client** (Go-based) — ещё одна либа с TLS impersonation
4. **Cloudflare Workers** — прокси через Cloudflare edge
5. **Ротация User-Agent + TLS** — менять fingerprint каждый запрос
