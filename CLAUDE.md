# Estate Invest — Инвестиционная компания

## Суть проекта
Документация, аналитика и инструменты для инвестиционной компании Estate Invest. Выкуп недвижимости ниже рынка → создание ценности → продажа с прибылью (50/50 с инвесторами).

## Масштаб
- 118 объектов (ИП), 900+ инвесторов
- ~196 млн покупка, ~388 млн продажа, ~37 млн прибыли инвесторам
- ИП Мудров Иван Юрьевич (ИНН 5903156505)

## Ключевые файлы
- `company-profile.md` — полный справочник компании (11 разделов, 708 строк)
- `company-profile.html` — визуальная HTML-версия
- `links.md` — все ссылки компании (138 строк)
- `ПЛАН_РЕАЛИЗАЦИИ.md` — этапы разработки Streamlit
- `СТРУКТУРА_ДАННЫХ.md` — схема Google Sheets (13 листов, 76K строк)
- `Code.gs` — Google Apps Script для монитора объектов

## Подпроекты

### Аналитика (Streamlit)
Папка `Аналитика/` — Python-приложение:
- `data_loader.py` — загрузчик из Google Sheets (gviz API, без ключей)
- `analytics.py` — расчёт метрик (инвесторы, объекты, портфель)
- `app.py` — Streamlit UI (6 вкладок)
- `config.py` — конфиг, маппинг листов
- Парсинг русского формата чисел ("5 228 170,99р." → 5228170.99)

### Командная панель
Папка `командная панель/` — 28 файлов исследования дизайна dashboard:
- `05-контент-карта.md` — PRD (7 KPI, 9 секций, 50 виджетов)
- Палитра: Midnight Indigo (#6366f1), glassmorphism, ApexCharts, Lucide Icons

## Технологический стек
- **Python**: Streamlit, Pandas, Requests
- **Frontend**: HTML/CSS/JS Vanilla, ApexCharts, Lucide, Leaflet.js
- **Данные**: Google Sheets (16 таблиц, основная: `1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0`)
- **CRM**: Битрикс24 (`estateinvest.bitrix24.ru`, REST API: `/rest/1/qlmnwa8sza8pvx14/`)
- **Бот**: Salebot (@Estate_invest_RF_bot, API key: `a27bfc4e3e8a7b856433529d75827851`, project 214444)

## Внешние системы
- **Сайт**: estateinvest.online (React SPA, ЛК для инвесторов)
- **Notion**: estateinvest.notion.site (страницы объектов)
- **SignEasy**: электронная подпись договоров
- **Telegram**: публичный + закрытый каналы, канал торгов

## Статус разработки Streamlit
- [x] Блок 1: DATA LOADER
- [x] Блок 2: ANALYTICS ENGINE
- [ ] Блок 3: ADMIN DASHBOARD (в процессе)
- [ ] Блок 4: INVESTOR PORTAL
- [ ] Блок 5: DEPLOY (Streamlit Cloud или VPS)

## Правила
- Финансовые данные — чувствительные, не публиковать
- Google Sheets — основной источник данных (16 таблиц)
- При работе с данными — учитывать мультивалютность (РУБ, $, €, USDT)
