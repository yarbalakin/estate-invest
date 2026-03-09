# Estate Invest — Полный реестр ссылок и credentials

> Обновлено: 07.03.2026
> Источники: links.md, HANDOFF.md, company-profile.md, MEMORY.md, torgi_monitor.py

---

## Google Sheets

| Spreadsheet ID | Название | Назначение |
|---|---|---|
| `1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0` | Основная таблица учёта | Транзакции (~76K строк), инвесторы, объекты, свода |
| `1oTRqpqS5GIunhi26TO8X6quWR5wWIWoTe0LzFqEGrDs` | Монитор объектов | 118 ИП, финансы, ROI, ссылки на Авито, 117 касс |
| `1Ulf_odOSRFcs4Ihi3waCo1Py_a0SgI3-FHlIKdCQvSU` | Таблица торгов | Лоты tbankrot.ru/m-ets.ru, статусы, даты, задатки |
| `1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk` | Монитор торгов — Лоты | Python-монитор (torgi.gov.ru + ЕФРСБ), 21 колонка |
| `1aRi5YLORBWDY5oU7hNo1XAWUoIvAM3ArxX7L2dbJHEc` | Касса компании | Движение денежных средств (закрытый) |
| `18S6crJXwHXCh1FKEzgc4444yn4T1KQd30ycpvmVx2Mk` | Статистика продаж | 7 листов: 2025, объекты, люди, доход инвесторов |
| `1lV3gZiWGX8IxsMbKHyMYCAfJB5BeGa33raIFqMLtthk` | Контент-план | 10 листов-календарей по каналам |
| `1odfnhaeg6HWRgiMu0ASuMPXTgSx673t6BUUoVh7JIts` | Шаблоны писем | Email: договор, welcome, уведомления |
| `1nwaS6lhg5SycS5B8gPQl3F-5qx6NuBeexnP782Nx_to` | Аккаунты соцсетей | VK-паблики, стратегия |
| `1DCxgwIKwJHSa5RwrCrqLUmb8ZCAFOnaHijtEfqXEiQA` | (неизвестно) | Закрытый доступ |
| `1fpyfpejSFW_3xw_XyVW7PX9YpBfxWAfL1yN9o5062Vo` | СКАУТ (Авито) | Сырые данные объявлений Авито |
| `1WaV19O7IwltPtUxHIzbHZwACF_bq1llPNPlBupTHEjc` | Аналитик Авито | AI-услуги + История отчётов |
| `1vXz68HpNyQXh3uJ-iklQfPgB2WeINUoSuXe-AYGwzZY` | Денежный бот | Транзакции: дата, категория, приход/расход |

---

## Сайт Estate Invest

| URL | Описание |
|---|---|
| https://estateinvest.online | Личный кабинет инвестора (главная) |
| https://estateinvest.online/sign-in | Вход в ЛК |
| https://estateinvest.online/dashboard/all-properties | Все объекты |
| https://estateinvest.online/dashboard/news | Новости |
| https://estateinvest.online/dashboard/faq | FAQ (SPA) |
| https://estateinvest.online/dashboard#portfolio | Портфель |
| https://estateinvest.online/dashboard#txs | Операции |
| https://estateinvest.online/dashboard#referral | Реферальная система |
| https://estateinvest.online/result | Результаты проекта |
| https://estateinvest.online/dashboard/setup-bot | Настройка бота |
| https://estateinvest.online/docs/terms | Политика конфиденциальности |
| https://estateinvest.online/?r=<КОД> | Реферальная ссылка (формат) |

---

## Telegram

### Каналы

| ID/Username | Описание |
|---|---|
| @russianestateincome | Публичный канал — новости, кейсы |
| t.me/+TOpOcVlVmJwxMWRj | Закрытый канал инвесторов |
| @torgiigrot | Канал торгов |
| t.me/+FtOHpdRQfPJmOWQy | Сообщество ФГ (практикум) |
| @topparsing (chat_id: `-1003759471621`) | "Лоты по Перми" — монитор торгов |

### Боты

| Токен | Username/Название | Назначение |
|---|---|---|
| `8650381430:AAFKGNZbjQmhAd3ogse9gOWs7_2xoypuo-A` | @monitor_estate_bot | Монитор торгов (VPS) |
| `8243536588:AAGQvqVUjcuIaWlg1N1Z830rwlOyaydbqZc` | Аналитик Авито | Ежедневные отчёты по объявлениям |
| `8604957943:AAF37XNjilxzwZV39MMTeGvVAalr95UrSpo` | Техн. уведомления | Claude Code hooks |
| `8250956506:AAEZSY-b-xdGaSeXhS4wADZIbdpF5fRH7L4` | Денежный бот | Учёт расходов/доходов |

### Chat IDs

| Chat ID | Кто |
|---|---|
| `191260933` | Ярослав (основной) |

---

## Битрикс24 CRM

| Параметр | Значение |
|---|---|
| Инстанс | `estateinvest.bitrix24.ru` |
| REST API | `https://estateinvest.bitrix24.ru/rest/1/qlmnwa8sza8pvx14/` |
| Скоупы | 73 |
| Сделки / Контакты / Лиды | 4 030 / 3 188 / 1 343 |
| Пользователей | 26 |
| Воронки | Инвестирование (0), Регистрация (2), Агентство (6), Эстейт продажи (8) |

---

## Salebot

| Параметр | Значение |
|---|---|
| Бот | @Estate_invest_RF_bot |
| Project ID | 214444 |
| API Key | `a27bfc4e3e8a7b856433529d75827851` |
| Endpoint | `chatter.salebot.pro/api/<key>/<action>` |
| Клиентов | 2 127 |
| Работает с | Март 2023 |

---

## Авито API

| Параметр | Значение |
|---|---|
| Client ID | `09mdH5WZURZgntFe9B49` |
| Client Secret | `4M1OpnyYcCV8sPZjEP27ednptjxoRvdZrHPUd45v` |
| User ID | `422949348` |
| Token endpoint | POST `https://api.avito.ru/token` (client_credentials) |
| Email | estatetorgi@yandex.ru |

Второй аккаунт (Аналитик):

| Параметр | Значение |
|---|---|
| User ID | 427914223 |
| Client ID | `rFREM-5Cj1o4AlZhVZQp` |

---

## n8n Cloud

| Параметр | Значение |
|---|---|
| Инстанс | `https://estateinvest.app.n8n.cloud` |

### Credentials (n8n)

| Credential | ID |
|---|---|
| Redis | `BLUkom4dAdgmswX1` |
| Telegram (Авито) | `len1hyHe6BeNXVS4` |
| Telegram (Денежный бот) | `jm6dd8L1v7OTVVaF` |
| Google Sheets | `EHQ0L5e8dznnC9ZT` |

### Workflows (Estate Invest)

| Workflow ID | Статус | Название |
|---|---|---|
| `H12Q90yhl9q1MNiI` | ACTIVE (заменён Python) | Монитор торгов (deprecated) |
| `RXbhtdi37u50TYQf` | DEV | Монитор торгов DEV |
| `IeavPlixA41UsGdX` | ACTIVE | Аналитик Авито — Ежедневный отчёт |
| `Etm8KIEVJzfBszGv` | ACTIVE | AI-услуги Авито — Аналитика |

---

## VPS (Монитор торгов)

| Параметр | Значение |
|---|---|
| IP | `5.42.102.36` |
| SSH | `ssh root@5.42.102.36` / пароль: `sp8hWiGY+kHsN6` |
| ОС | Ubuntu 24.04, Timeweb Cloud, 350 руб/мес |
| Код | `/opt/torgi-proxy/` |
| Скрипты | `torgi_monitor.py`, `efrsb_monitor.py`, `main.py` |
| Cron | `0 */4 * * *` (оба скрипта) |
| Systemd | `torgi-proxy.service` (FastAPI на 8080) |
| Proxy API | `http://127.0.0.1:8080/api/torgi` (ключ: `ei-torgi-2026-mvp`) |

---

## GitHub

| URL | Тип | Описание |
|---|---|---|
| https://github.com/yarbalakin/estate-invest | Приватный | Основной код |
| https://github.com/yarbalakin/estate-invest-academy | Публичный | GitHub Pages |
| https://yarbalakin.github.io/estate-invest-academy/ | Сайт | index.html, ai-analytics.html |

---

## Внешние API

| Endpoint | Описание |
|---|---|
| `https://ads-api.ru/main/api` | Агрегатор ЦИАН+Авито+Домклик (user: yabalakin@yandex.ru, token: de5f6b...) |
| `https://api.avito.ru/token` | Авито OAuth |
| `https://openrouter.ai/api/v1/chat/completions` | AI (Llama 3.3 70B, free) |
| `https://queue.fal.run/fal-ai/flux-pro/v1.1` | Генерация фото (Flux Pro, $0.05/шт) |
| `https://torgi.gov.ru/new/public/lots/lot/<id>` | Карточка лота торгов |
| `https://fedresurs.ru` | ЕФРСБ (банкротства) |

---

## Notion

| URL | Описание |
|---|---|
| https://estateinvest.notion.site | Корневая страница |
| https://estateinvest.notion.site/31-319-... | ИП №31 (Соликамская) |
| https://estateinvest.notion.site/70-Estate-Invest-... | ИП №70 (Партнёрское) |

---

## Соцсети

| URL | Описание |
|---|---|
| https://vk.com/estateinvest.online | Основной паблик |
| https://vk.com/gleb_khrianin | Глеб |
| https://vk.com/realtwingleb | Глеб (альт.) |
| https://vk.com/ivanmudrov | Иван |
| https://dzen.ru/estateinvest | Дзен |

---

## Google Drive / Dropbox / Docs

| URL | Описание |
|---|---|
| https://drive.google.com/drive/folders/1d69F1D8WuCw1fZhs4fwBQ1KrOrLIlzaW | Корневая папка (12 подпапок) |
| https://docs.google.com/document/d/1M8nbyRvb7nEPgKUl9D4RYdkTXQQCA9gj/edit | Инвестиционный договор |
| https://docs.google.com/document/d/1t-NLglsvON2JobBdKO-07JA-m13_3nt5InMIxfMEl-8/edit | Заявление на вывод |
| https://paper.dropbox.com/folder/show/e.1gg8YzoPEhbTkrhvQwJ2zzS47SQ... | Регламенты (закрытый) |
| https://paper.dropbox.com/folder/show/e.1gg8YzoPEhbTkrhvQwJ2zzS1LMy... | Документы (закрытый) |
| https://paper.dropbox.com/doc/Salebot--B4H7VZz5w3UGcD... | Документация Salebot |

---

## Прочее

| URL | Описание |
|---|---|
| https://telegra.ph/Nashi-rezultaty-04-17-2 | Результаты (Telegra.ph) |
| https://clck.ru/34ciFz | Инструкция ЛК на смартфон |
| tbankrot.ru | Парсинг лотов (логин: estatetorgi@yandex.ru / agent2025) |
