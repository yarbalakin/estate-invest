# DataLens и Looker Studio: пошаговые гайды

---

## Yandex DataLens + Google Sheets

### Пошаговая настройка

**Шаг 1. Подготовка таблицы:**
- Открыть Google Sheets → "Настройки доступа" → "Все, у кого есть ссылка" → "Читатель"
- Скопировать ссылку

**Шаг 2. Создание подключения в DataLens:**
- Открыть https://datalens.yandex.cloud/ (бесплатно, нужен Яндекс-аккаунт)
- Подключения → Создать подключение → Google Sheets
- Вставить ссылку → зелёный значок = ОК → Создать

**Шаг 3. Датасет:**
- Датасеты → Создать → выбрать подключение → выбрать лист
- Поля: удалить ненужные, исправить типы (Дата, Число, Строка), задать агрегацию
- Можно создать вычисляемые поля (формулы DataLens)

**Шаг 4. Чарты:**
- Создать чарт → выбрать датасет → выбрать тип визуализации
- Перетащить поля в X, Y, Цвет, Размер, Фильтры

**Шаг 5. Дашборд:**
- Создать дашборд → Добавить → Чарт
- Добавить селекторы (фильтры)
- Расположить на сетке → Сохранить

Источник: https://vc.ru/id1240117/458255

### Лимиты

| Параметр | Лимит |
|----------|-------|
| Макс. размер листа | 200 МБ |
| Макс. столбцов | 300 |
| Кэш Google Sheets | до 5 минут |
| Чартов на дашборде | Без ограничений (но производительность) |
| Стоимость | Бесплатно (Community) |

---

## DataLens + Битрикс24

### Способ 1: Нативный BI-коннектор (самый быстрый)

1. В Битрикс24: **CRM → Аналитика → BI-аналитика → вкладка "Yandex DataLens"**
2. Скопировать **Адрес сервера** и **Секретный ключ**
3. В DataLens: Создать подключение → тип "Битрикс24"
4. Вставить сервер + ключ
5. Автоматически создаётся: датасеты (crm_lead, crm_deal, crm_contact, crm_company) + готовый дашборд с 3 вкладками

**Ограничения**: нужен Professional тариф Б24, обновление каждые 12 часов.

Источники:
- https://o2k.ru/blog/yandex-datalens-i-bitrix24
- https://helpdesk.bitrix24.ru/open/17402692/
- Приложение в маркетплейсе: https://www.bitrix24.ru/apps/app/sites7.dashboard_datalens/

### Способ 2: Через промежуточную БД (Хабр)

1. Создать входящий вебхук в Б24
2. Docker-скрипт → выгрузка в PostgreSQL/ClickHouse
3. Yandex Cloud Functions как observer
4. DataLens → PostgreSQL напрямую

Источник: https://habr.com/ru/companies/yandex_cloud_and_infra/articles/762534/

### Способ 3: Google Sheets как прокси

Битрикс24 → Albato/Make → Google Sheets → DataLens

- Albato Б24 + Sheets: https://albato.ru/integration-bitrix24-googlesheets
- Albato DataLens + Sheets: https://albato.ru/integration-yandexdatalens-googlesheets

---

## DataLens: типы визуализаций

| Тип | Для чего |
|-----|----------|
| Линейная диаграмма | Динамика во времени |
| Диаграмма с областями | Динамика с накоплением |
| Столбчатая | Сравнение категорий |
| Линейчатая (Bar) | Горизонтальное сравнение |
| Точечная (Scatter) | Корреляция |
| Круговая | Доли |
| Кольцевая | Доли с центром |
| Treemap | Иерархия |
| Таблица | Детальные данные |
| Сводная (Pivot) | Кросс-таблица |
| Индикатор (KPI) | Одно ключевое число |
| Карта | Гео-данные |

**Воронка**: через горизонтальную столбчатую с сортировкой стадий сверху вниз.

### Примеры и галерея
- Галерея DataLens: https://datalens.ru/gallery
- Marketplace с шаблонами
- Кейс ритейл: https://datanomics.ru/artciles/postroenie-dashborda-v-yandex-datalens-na-primere-prognozirovaniya-sprosa-v-ritejle/
- Кейс маркетинг: https://ppc.world/articles/kak-postroit-skvoznuyu-analitiku-v-yandex-datalens/
- Кейс веб-аналитика: https://habr.com/ru/articles/756374/
- Усложнённые примеры: https://babok-school.ru/blog/interactive-dashboard-in-datalens/

---

## DataLens Self-hosted (Docker)

**GitHub**: https://github.com/datalens-tech/datalens

| Параметр | Минимум |
|----------|---------|
| RAM | 4 GB |
| CPU | 2 ядра |
| Docker Compose | v2 |

```bash
git clone https://github.com/datalens-tech/datalens && cd datalens
HC=1 docker compose up
# Доступ: http://localhost:8080
```

### Cloud vs Self-hosted

| | Cloud | Self-hosted |
|---|---|---|
| Google Sheets | Да | **Нет** |
| Битрикс24 | Да | **Нет** |
| Стоимость | Бесплатно | Свои серверы |

**Вывод**: для Estate Invest облачная версия лучше (есть Sheets + Б24 коннекторы).

---

## Google Looker Studio

### Подключение Google Sheets (2 клика)

1. https://lookerstudio.google.com → Создать → Источник данных → Google Таблицы
2. Выбрать таблицу и лист → Подключить
3. Настроить типы полей → Создать отчёт

### Подключение Битрикс24

**Нативный BI-коннектор**: CRM → Аналитика → BI-аналитика → вкладка "Google Looker Studio"
**Через Kondado**: https://kondado.io/en/dataviz/looker-studio-bitrix24-crm.html — настройка за 5 мин

### Looker Studio шаблоны
- 60+ бесплатных: https://windsor.ai/data-studio-template-gallery/
- 23 примера: https://supermetrics.com/blog/looker-studio-examples
- Визуализация воронок: https://measureschool.com/funnel-visualization-in-looker-studio/

---

## DataLens vs Looker Studio: итоговое сравнение

| | DataLens | Looker Studio |
|---|---|---|
| Google Sheets | Да (кэш 5 мин) | Да (realtime) |
| Битрикс24 | Нативный коннектор | Через BI-коннектор/Kondado |
| Язык | Русский | Английский |
| Стоимость | Бесплатно | Бесплатно |
| Шаблоны | Marketplace | 800+ |
| Серверы РФ | Да | Нет |

---

## Google Sheets как DWH

### Лимиты

| Параметр | Лимит |
|----------|-------|
| Ячеек на файл | 10 000 000 |
| IMPORTRANGE | 10 МБ на вызов |
| IMPORTRANGE | 50-100K ячеек на формулу |

### Паттерны IMPORTRANGE
```
=QUERY(IMPORTRANGE("url","Sheet1!A:F"), "SELECT Col1, SUM(Col3) GROUP BY Col1")
```

**Правильно**: агрегировать в исходной таблице, импортировать итог.
**Неправильно**: цепочки A→B→C, миллионы ячеек, много формул в одной таблице.

### Apps Script для автоматизации
- Триггеры: каждые 1-30 мин, 1-12 часов, ежедневно
- Лимит: 6 мин на скрипт, 90 мин суммарно/сутки
- Для обхода: разбивать задачу, сохранять прогресс в PropertiesService
