# Advanced Metrics & Analytical Frameworks для Estate Invest

> Deep Research: продвинутые метрики, формулы и фреймворки для инвестиционной компании недвижимости.
> Дата: 25.02.2026

---

## Содержание

1. [Fund Performance Metrics (IRR, MOIC, DPI, TVPI, PME)](#1-fund-performance-metrics)
2. [Waterfall Distribution & Gross vs Net Returns](#2-waterfall-distribution--gross-vs-net-returns)
3. [Portfolio Health & Risk Metrics](#3-portfolio-health--risk-metrics)
4. [Operational Efficiency Metrics](#4-operational-efficiency-metrics)
5. [Investor Relations Metrics](#5-investor-relations-metrics)
6. [Market Intelligence Metrics](#6-market-intelligence-metrics)
7. [Financial Health Metrics](#7-financial-health-metrics)
8. [Predictive Metrics (Leading Indicators)](#8-predictive-metrics-leading-indicators)
9. [Composite Scores & Indices](#9-composite-scores--indices)
10. [Benchmarking](#10-benchmarking)
11. [Cohort Analysis for Investors](#11-cohort-analysis-for-investors)
12. [Implementation Roadmap для Estate Invest](#12-implementation-roadmap)

---

## 1. Fund Performance Metrics

### 1.1 IRR — Internal Rate of Return (Внутренняя норма доходности)

**Формула**: Ставка дисконтирования r, при которой NPV = 0:

```
Σ [CFt / (1 + IRR)^t] = 0
```

Где CFt — денежный поток в период t (отрицательный для вложений, положительный для выплат).

**Почему важно**: IRR учитывает ВРЕМЯ денег. Доходность 30% за 3 месяца и 30% за 18 месяцев — это кардинально разные результаты. Простой ROI этого не показывает.

**Два вида IRR**:

| Вид | Формула | Что показывает |
|-----|---------|----------------|
| **Gross IRR** | До вычета комиссий и расходов | Эффективность инвестиционных решений GP |
| **Net IRR** | После вычета всех комиссий | Реальная доходность для инвестора (LP) |

**Что "хорошо"**:
- Top-quartile RE PE фонды: Net IRR 15-20%+
- Estate Invest benchmark: завершённые объекты показывают 10-40% ROI за 3-18 мес. В пересчёте на IRR это ~20-100%+ годовых (отличный результат)

**Применение к Estate Invest**:
- Считать IRR для КАЖДОГО ИП индивидуально (дата вложения → дата выплаты тела + %)
- Средневзвешенный IRR портфеля по всем завершённым объектам
- Пример: ИП №40 (34.27% за 18 дней) = IRR ~690% годовых; ИП №23 (42.37% за 15 мес) = IRR ~32% годовых

### 1.2 MOIC — Multiple on Invested Capital

**Формула**:

```
MOIC = Совокупные выплаты / Совокупные вложения
```

**Для Estate Invest**:

```
MOIC = (Тело + Прибыль инвестора) / Начальное вложение
```

При модели 50/50: если объект куплен за 1 млн, продан за 1.5 млн (прибыль 500к, инвесторам — 250к):

```
MOIC = (1 000 000 + 250 000) / 1 000 000 = 1.25x
```

**Что "хорошо"**:
- 1.0x = вернул то что вложил (ноль прибыли)
- 1.2-1.5x = хороший результат для 6-12 мес цикла
- 2.0x+ = отличный результат
- Estate Invest средний MOIC: ~1.15-1.25x (при доходности 10-40% и доле 50%)

**Почему важно**: MOIC понятен любому инвестору — "вложил 100к, получил 125к, мультипликатор 1.25x". Проще IRR для коммуникации.

### 1.3 TVPI — Total Value to Paid-In Capital

**Формула**:

```
TVPI = (Распределённые выплаты + Текущая стоимость нереализованных активов) / Общий вложенный капитал
```

```
TVPI = DPI + RVPI
```

**Для Estate Invest**:

```
TVPI = (37 млн выплат + NAV текущих объектов) / Общая сумма вложений всех инвесторов
```

**Что "хорошо"**:
- TVPI > 1.5x за 3-5 лет — top quartile
- Estate Invest: нужно посчитать NAV текущего портфеля (118 объектов, ~388 млн оценочная продажа)

### 1.4 DPI — Distributed to Paid-In Capital

**Формула**:

```
DPI = Совокупные выплаты инвесторам / Совокупный вложенный капитал
```

**Почему важно**: DPI показывает РЕАЛИЗОВАННУЮ доходность — сколько денег реально вернулось инвесторам. TVPI включает "бумажную" стоимость, а DPI — только кэш.

**Что "хорошо"**:
- DPI > 1.0 = инвесторы уже вернули больше чем вложили
- DPI > 0.5 к 3-му году жизни фонда — хороший темп

**Для Estate Invest**:
- 37 млн распределённой прибыли + возврат тел = DPI
- Критически важная метрика для доверия инвесторов

### 1.5 RVPI — Residual Value to Paid-In Capital

**Формула**:

```
RVPI = NAV текущего портфеля / Совокупный вложенный капитал
```

**Для Estate Invest**: RVPI = стоимость нереализованных объектов (в стадии "реализация" и "сбор средств"), приведённая к текущей рыночной оценке, делённая на вложения в эти объекты.

Высокий RVPI означает большой нереализованный потенциал. Но инвесторы предпочитают видеть рост DPI (реальные деньги).

### 1.6 PME — Public Market Equivalent

**Формула** (метод Long-Nickels):

```
PME IRR Spread = IRR фонда − IRR гипотетического вложения в индекс
```

Механика: каждый capital call "покупает" индекс, каждая distribution "продаёт" индекс, сравнивается финальная стоимость.

**Формула** (Kaplan-Schoar):

```
KS-PME = FV(distributions) / FV(capital calls)
```

Где FV рассчитывается через доходность публичного индекса за тот же период.

- KS-PME > 1.0 = фонд обыграл рынок
- KS-PME < 1.0 = рынок был лучше

**Для Estate Invest**: Сравнивать с MOEX (Московская биржа) или банковскими депозитами (текущая ставка ~18-21% годовых). При IRR 30%+ Estate Invest значительно обгоняет оба бенчмарка.

### 1.7 J-Curve (J-кривая)

**Концепция**: Графическое представление доходности фонда во времени.

```
Доходность
    ^
    |              ___________
    |             /
    |            /
    |           /
----+----------/-----------> Время
    |    \    /
    |     \__/    ← Этап "создания ценности"
    |
```

**Фазы**:
1. **Инвестиционный период** (0-6 мес): вложения > выплат, IRR отрицательный (покупка, ремонт, расходы)
2. **Точка перелома** (6-12 мес): первые продажи, IRR стремится к 0
3. **Реализация** (12+ мес): продажи накапливаются, IRR растёт

**Для Estate Invest**: J-кривая объясняет инвесторам почему в первые месяцы "ничего не происходит". Визуализация J-кривой на дашборде — мощный инструмент управления ожиданиями.

---

## 2. Waterfall Distribution & Gross vs Net Returns

### 2.1 Модель водопада (Waterfall)

Текущая модель Estate Invest (50/50) — это простой waterfall без hurdle rate. Продвинутая модель:

| Тир | Порог | Распределение |
|-----|-------|---------------|
| **Return of Capital** | До возврата тела | 100% инвесторам |
| **Preferred Return (Pref)** | 8-10% годовых | 100% инвесторам |
| **GP Catch-Up** | До выравнивания | 100% GP (Estate Invest) |
| **Carried Interest** | Выше pref | 70/30 или 80/20 (LP/GP) |

**Для Estate Invest**: Текущая модель 50/50 проще и прозрачнее. Но если средний срок объекта 6 мес, а доходность 25%, то:
- Инвестор получает: 12.5% за 6 мес (25% годовых)
- Компания получает: 12.5%

При waterfall с pref 15% годовых:
- Инвестор получает pref: 7.5% за 6 мес
- Остаток (25% - 7.5% = 17.5%) делится 20/80 GP/LP
- Инвестор итого: 7.5% + 14% = 21.5% (vs 12.5% при 50/50)
- Но GP получает меньше при высокой доходности, больше стимула для quick flips

### 2.2 Gross vs Net Returns

**Формулы**:

```
Gross Return = (Цена продажи - Цена покупки) / Цена покупки × 100%

Net Return (для инвестора) = Gross Return × Доля инвестора - Расходы на содержание
```

**Для Estate Invest**:

```
Gross = (388 млн - 196 млн) / 196 млн = 97.9% (совокупный)
Net (инвесторам) = 37 млн / Совокупные вложения × 100%
```

Разница Gross → Net показывает эффективность структуры расходов. Типичная "потеря" в PE фондах: 500-800 bps (basis points). У Estate Invest при 50/50 модели "потеря" = 50% + операционные расходы.

---

## 3. Portfolio Health & Risk Metrics

### 3.1 HHI — Herfindahl-Hirschman Index (Концентрация)

**Формула**:

```
HHI = Σ (Si)²
```

Где Si — доля i-го сегмента в портфеле (в %).

**Пример для Estate Invest по географии**:
- Пермь: 60% → 3600
- Калининград: 20% → 400
- Самара: 10% → 100
- Другие: 8% → 64
- Турция: 2% → 4
- **HHI = 4168** (высокая концентрация!)

**Интерпретация**:
- < 1500 = низкая концентрация (хорошо диверсифицировано)
- 1500-2500 = умеренная концентрация
- > 2500 = высокая концентрация (РИСК)

**По типам объектов**:
- Земля: 70% → 4900
- Жилая: 15% → 225
- Коммерческая: 10% → 100
- Авто: 3% → 9
- Зарубежная: 2% → 4
- **HHI = 5238** (очень высокая концентрация на земле!)

**Рекомендация**: HHI > 4000 — серьёзный красный флаг. Нужна диверсификация по типам объектов или осознанное принятие этого риска.

### 3.2 Vintage Diversification (Диверсификация по "поколениям")

**Концепция**: Группировка объектов по дате покупки (квартал/полугодие). Если 80% объектов куплены в одном квартале — весь портфель зависит от рыночных условий ЭТОГО периода.

**Формула** (Vintage Concentration):

```
Vintage HHI = Σ (доля вложений в квартал i)²
```

**Для Estate Invest**: С 118 объектами за ~2 года, если покупки распределены равномерно (~15 объектов/квартал), HHI будет низким (хорошо). Если были "кластеры" покупок — риск.

### 3.3 Liquidity Score (Коэффициент ликвидности портфеля)

**Формула**:

```
Liquidity Score = Σ (Стоимость объекта × Коэффициент ликвидности типа) / Общая стоимость портфеля
```

Коэффициенты ликвидности (дни до продажи → балл):
- < 30 дней: 1.0 (высоколиквидный)
- 30-90 дней: 0.7
- 90-180 дней: 0.4
- > 180 дней: 0.1

**Для Estate Invest**: Земельные участки обычно менее ликвидны (0.3-0.5), квартиры более ликвидны (0.7-0.9). При 70% земли — Liquidity Score будет низким.

### 3.4 Portfolio Age Distribution (Возрастная структура)

**Формула**:

```
Weighted Average Age = Σ (Возраст объекта в днях × Стоимость объекта) / Общая стоимость портфеля
```

**"Застрявшие" объекты** — отдельная метрика:

```
Stale Ratio = Кол-во объектов с возрастом > 2× среднего / Общее кол-во объектов
```

**Для Estate Invest**: Если средний срок 6 мес, а есть объекты по 18+ мес — это сигнал проблемы. Stale Ratio > 15% требует внимания.

### 3.5 Maximum Drawdown (Максимальная просадка)

**Формула**:

```
Max Drawdown = (Пиковая NAV - Минимальная NAV) / Пиковая NAV × 100%
```

Показывает наихудший период в жизни портфеля. Инвесторы должны знать этот риск.

### 3.6 Size Concentration Risk

**Формула**:

```
Top-5 Concentration = Стоимость 5 крупнейших объектов / Общая стоимость портфеля
```

**Для Estate Invest**: ИП №31 (29.4 млн) + ИП №91 (21 млн) + ИП №92 (15.7 млн) + ИП №70 (8 млн) + ИП №35 (8.5 млн) = 82.6 млн. Если общий портфель ~196 млн, Top-5 = 42%. Это ВЫСОКАЯ концентрация — один проблемный объект может повлиять на весь результат.

---

## 4. Operational Efficiency Metrics

### 4.1 Sales Velocity (Скорость продаж)

**Формула**:

```
Sales Velocity = (Кол-во объектов в продаже × Средняя стоимость × Win Rate) / Средний цикл продажи (дней)

= Рублей в день, генерируемых pipeline-ом
```

**Пример для Estate Invest**:
- 46 объявлений на Авито
- Средняя стоимость продажи: ~3.3 млн (388 / 118)
- Win Rate (конверсия показ → сделка): 20%
- Средний цикл: 45 дней (цель)

```
Velocity = (46 × 3 300 000 × 0.20) / 45 = 675 000 руб/день
```

### 4.2 Time-to-Value (Время создания ценности)

**Формула**: Общий цикл разбивается на этапы:

```
Time-to-Value = T(поиск) + T(выкуп) + T(оформление) + T(ремонт) + T(продажа) + T(выплата)
```

| Этап | Целевое | Текущее (оценка) | Формула эффективности |
|------|---------|------------------|-----------------------|
| Поиск → Выкуп | 30 дней | ? | T(screening) / Conversion = Leads needed |
| Выкуп → Старт работ | 14 дней | ? | Административная задержка |
| Ремонт/Подготовка | 30-60 дней | ? | План vs Факт |
| Размещение → Продажа | 45 дней | ? | Days on Market |
| Продажа → Выплата | 14 дней | ? | Settlement speed |
| **Итого** | **~4-6 мес** | **3-18 мес** | Variance = сигнал проблемы |

### 4.3 Renovation Efficiency Ratio (Эффективность ремонта)

**Формула**:

```
Renovation Efficiency = Бюджет ремонта (план) / Бюджет ремонта (факт)
```

- 1.0 = точно по плану
- > 1.0 = экономия (отлично)
- < 1.0 = перерасход
- 0.7 = 30% перерасход (красная зона)

**Бенчмарк**: 90% строительных проектов имеют перерасход, средний перерасход — 28%. Если Estate Invest держит < 10% — это ОТЛИЧНЫЙ результат. Текущий KPI: отклонение < 10%.

**Value-Add Efficiency**:

```
Value-Add Ratio = (Рыночная стоимость после ремонта - Стоимость до ремонта) / Стоимость ремонта
```

- 2.0x = каждый рубль ремонта создаёт 2 рубля добавленной стоимости (отлично)
- 1.5x = хороший результат
- < 1.0x = ремонт уничтожает ценность

### 4.4 Pipeline Velocity по стадиям

```
Стадия          | Кол-во | Avg время | Conversion | Bottleneck?
-----------------------------------------------------------------
Скрининг        |   50   |  7 дней   |   10%      |    Нет
Анализ          |    5   | 14 дней   |   60%      |    Нет
Торги           |    3   | 21 день   |   66%      |    Возможно
Выкуп           |    2   | 30 дней   |   90%      |    Нет
Ремонт          |    5   | 60 дней   |   95%      |    ⚠️ Узкое место
Продажа         |   10   | 45 дней   |   85%      |    ⚠️ Возможно
Выплата         |    3   |  7 дней   |  100%      |    Нет
```

**Формула Bottleneck Score**:

```
Bottleneck Score = (Фактическое время на стадии / Целевое время) × (1 / Conversion rate)
```

Стадия с максимальным Bottleneck Score — узкое место системы.

### 4.5 Staff Productivity

**Формула**:

```
Deals per Person = Завершённых объектов / Кол-во сотрудников в процессе
Revenue per Person = Выручка / Кол-во сотрудников
Capital Efficiency = Прибыль / Операционные расходы на персонал
```

**Для Estate Invest** (~13 человек, ~120 объектов за 2 года):
- ~9 объектов на человека в год
- При ~72 млн выручки: ~5.5 млн на человека

### 4.6 Auction Win Rate

**Формула**:

```
Auction Win Rate = Выигранные торги / Участия в торгах × 100%
```

**Дополнительно**:

```
Discount to Market = (Рыночная цена - Цена покупки) / Рыночная цена × 100%
```

Текущий KPI: скидка > 30%. Это отличный benchmark.

---

## 5. Investor Relations Metrics

### 5.1 NAV Tracking (Отслеживание стоимости активов)

**Формула** (для каждого инвестора):

```
Personal NAV = Σ (Доля в объекте × Текущая оценочная стоимость объекта) + Доступные средства на счёте
```

**Portfolio NAV** (для всей компании):

```
Company NAV = Σ (Рыночная стоимость всех объектов) - Обязательства
```

**NAV per Investor Share**:

```
NAV/Share = Company NAV / Общее кол-во "долей"
```

### 5.2 Distribution Yield (Доходность выплат)

**Формула**:

```
Distribution Yield = Выплаты за период / Средний NAV за период × 100%
```

**Для Estate Invest**: Если за квартал выплачено 5 млн прибыли при среднем NAV 200 млн:

```
Distribution Yield = 5 / 200 = 2.5% за квартал = 10% годовых
```

### 5.3 Capital Deployment Rate (Скорость размещения капитала)

**Формула**:

```
Deployment Rate = Размещённый капитал / Общий доступный капитал × 100%
```

**Idle Capital Ratio**:

```
Idle Ratio = Свободные средства инвесторов на счетах / Общий капитал
```

Если у инвесторов "лежат" деньги без вложения > 30 дней — это потерянная доходность и риск оттока.

### 5.4 Investor Churn & Retention

**Формулы**:

```
Monthly Churn = Инвесторов ушло за месяц / Инвесторов на начало месяца × 100%

Retention Rate = 1 - Churn Rate

Dollar Retention = Капитал оставшихся инвесторов на конец / Капитал на начало × 100%
```

**Net Dollar Retention** (включая довложения):

```
NDR = (Начальный капитал + Довложения - Отток) / Начальный капитал × 100%
```

- NDR > 100% = инвесторы вкладывают больше чем выводят (рост без привлечения новых!)
- NDR > 120% = отличный результат
- NDR < 90% = красный флаг

**Текущий KPI Estate Invest**: отток < 5% в квартал = < 20% годовых churn. Для финансовых продуктов это приемлемо, но NDR важнее.

### 5.5 NPS — Net Promoter Score

**Формула**:

```
NPS = % Промоутеров (9-10) - % Детракторов (0-6)
```

**Бенчмарк для RE**: средний NPS = 30. Выше 50 — отличный результат.

**Как измерять**: Раз в квартал, простой опрос в Telegram-боте: "Насколько вероятно, что вы порекомендуете Estate Invest друзьям? (0-10)"

**Дополнительно — eNPS (Employee)**:

```
eNPS = % Промоутеров среди команды - % Детракторов среди команды
```

### 5.6 Communication Frequency Score

**Формула**:

```
Communication Score = (Обновлений по объектам / месяц) / Кол-во активных объектов
```

- < 0.5 = мало коммуникации (инвесторы волнуются)
- 1.0 = одно обновление на объект в месяц (минимум)
- 2.0+ = отлично

### 5.7 Reinvestment Rate (Ставка реинвестирования)

**Формула**:

```
Reinvestment Rate = Объём реинвестированной прибыли / Общий объём выплат × 100%
```

Если инвесторы получают выплату и сразу вкладывают в новый объект — это показатель доверия.
- > 60% = отлично (инвесторы верят в компанию)
- 30-60% = нормально
- < 30% = инвесторы выводят деньги (проблема)

---

## 6. Market Intelligence Metrics

### 6.1 Price per SQM Trends (Цена за м²)

**Формулы**:

```
Average Price/m² = Σ (Цена продажи / Площадь) / Кол-во продаж

Price Premium = (Наша цена продажи/м² - Средняя рыночная/м²) / Средняя рыночная × 100%

Price Discount at Purchase = (Рыночная цена/м² - Наша цена покупки/м²) / Рыночная × 100%
```

### 6.2 Days on Market (DOM) — Дни на рынке

**Формула**:

```
DOM = Дата продажи - Дата размещения объявления
```

**Бенчмарки**:
- Квартиры (Пермь): 30-60 дней — нормально, < 30 — быстро
- Земля: 60-120 дней — нормально
- Коммерческая: 90-180 дней — нормально

**DOM Efficiency**:

```
DOM Efficiency = Целевой DOM / Фактический DOM
```

- > 1.0 = продаём быстрее цели (снижать цену не обязательно, но может быть признак заниженной цены)
- < 0.5 = продаём в 2x медленнее (переоценка или плохой маркетинг)

### 6.3 Lead Response Time

**Формула**:

```
Avg Response Time = Σ (Время первого ответа - Время заявки) / Кол-во заявок
```

**Бенчмарк**: < 5 минут = максимальная конверсия. Каждый час задержки снижает конверсию на 10-15%.

### 6.4 Absorption Rate (Скорость поглощения рынком)

**Формула**:

```
Absorption Rate = Кол-во продаж за месяц / Кол-во объектов на рынке
```

- > 20% = рынок продавца (можно поднимать цены)
- 10-20% = сбалансированный рынок
- < 10% = рынок покупателя (снижать цены или ждать)

### 6.5 Avito Analytics (специфично для Estate Invest)

```
Avito CTR = Просмотры объявления / Показы в поиске × 100%
Avito Conversion = Контакты (звонки+сообщения) / Просмотры × 100%
Avito Position = Средняя позиция объявления в поиске
Avito Favorites/Views = Добавлений в избранное / Просмотры (показатель интереса)
```

---

## 7. Financial Health Metrics

### 7.1 Cash Runway (Запас денежных средств)

**Формула**:

```
Cash Runway (мес.) = Свободные денежные средства / Среднемесячный расход (burn rate)
```

**Burn Rate**:

```
Monthly Burn = Зарплаты + Аренда + Маркетинг + Операционные расходы
```

**Для Estate Invest**: Если monthly burn ~1.5 млн (13 человек × ~80к ср. + прочие) и на счёте 5 млн:

```
Runway = 5 / 1.5 = 3.3 мес
```

**Что "хорошо"**: Runway > 6 месяцев = безопасно. < 3 мес = красная зона.

### 7.2 Working Capital Ratio (Коэффициент оборотного капитала)

**Формула**:

```
Working Capital Ratio = Текущие активы / Текущие обязательства
```

- > 2.0 = отлично (большой запас)
- 1.2-2.0 = здоровый диапазон
- < 1.0 = компания не может покрыть текущие обязательства (кризис)

### 7.3 DSCR — Debt Service Coverage Ratio

**Формула**:

```
DSCR = Чистый операционный доход (NOI) / Обслуживание долга (проценты + тело)
```

- > 1.25 = здоровый уровень (большинство банков требуют минимум 1.25)
- 1.0 = на грани (доход = платежи)
- < 1.0 = не хватает дохода на обслуживание долга

**Для Estate Invest**: Если используется заёмный капитал для выкупа объектов, DSCR критичен.

### 7.4 Revenue Predictability Score

**Формула**:

```
Predictability = 1 - (Стандартное отклонение месячной выручки / Средняя месячная выручка)
```

- 0.8-1.0 = стабильный, предсказуемый бизнес
- 0.5-0.8 = умеренная волатильность (типично для flip-модели)
- < 0.5 = высокая непредсказуемость

**Для Estate Invest**: Flip-модель inherently непредсказуема (продажи кластеризуются). Это НОРМАЛЬНО, но нужен pipeline для сглаживания.

### 7.5 Capital Turnover Ratio (Оборачиваемость капитала)

**Формула**:

```
Capital Turnover = Годовая выручка от продаж / Средний задействованный капитал
```

- 2.0x = капитал оборачивается 2 раза в год (средний объект: 6 мес цикл)
- 1.0x = один раз в год
- > 3.0x = очень быстрый оборот

**Для Estate Invest**: 72 млн выручки / ~196 млн капитал = 0.37x. Это означает, что большая часть капитала "заморожена" в нереализованных объектах. Ускорение оборачиваемости — ключ к росту.

---

## 8. Predictive Metrics (Leading Indicators)

### 8.1 Pipeline-to-Close Ratio

**Формула**:

```
Pipeline-to-Close = Объектов в pipeline / Среднее кол-во закрытий в месяц
```

- Результат = "месяцы запаса pipeline"
- < 3 мес = нужно усиливать sourcing
- 6-12 мес = здоровый pipeline
- > 18 мес = pipeline раздут (объекты "застревают")

**Для Estate Invest**: 46 объявлений на Авито / ~5-10 продаж/мес = 4.6-9.2 мес pipeline. Здоровый диапазон.

### 8.2 Inquiry-to-Showing Ratio

**Формула**:

```
Inquiry-to-Showing = Кол-во показов / Кол-во входящих заявок × 100%
```

- > 50% = хорошая квалификация лидов
- 20-50% = нормально
- < 20% = плохая квалификация или нерелевантный трафик

### 8.3 Traffic Leading Indicator

**Формула**:

```
Traffic Momentum = Просмотры Авито за текущую неделю / Просмотры за предыдущую неделю
```

- > 1.1 = рост интереса (ожидай больше сделок через 2-4 недели)
- 0.9-1.1 = стабильно
- < 0.9 = падение интереса (действуй: снижай цены, улучшай объявления)

### 8.4 Investor Sentiment Leading Indicator

**Формулы**:

```
Capital Inflow Momentum = Новые вложения за месяц / Средние вложения за 3 мес
New Investor Momentum = Новые инвесторы за месяц / Среднее за 3 мес
```

- Momentum > 1.2 = позитивный тренд (расширяй pipeline объектов)
- Momentum < 0.8 = снижение интереса (усиль маркетинг, проведи мероприятие)

### 8.5 Auction Market Leading Indicators

```
Auction Supply Trend = Кол-во лотов на торгах за квартал / Предыдущий квартал
Average Lot Price Trend = Средняя начальная цена лота / Предыдущий период
Competition Index = Среднее кол-во участников торгов / Предыдущий период
```

Рост supply + падение competition = "золотое окно" для закупки.

### 8.6 Predictive Deal Score

**Формула**: Скоринг каждого потенциального объекта перед покупкой:

```
Deal Score = w1 × Discount% + w2 × Liquidity + w3 × Location + w4 × Type + w5 × Size

Где:
- Discount%: скидка от рынка (0-100, нормализовано)
- Liquidity: оценка ликвидности (0-100)
- Location: привлекательность локации (0-100)
- Type: тип объекта (земля, жилая, комм.) → исторический success rate
- Size: размер сделки vs средний (штраф за слишком большие)

Веса (пример): w1=0.30, w2=0.25, w3=0.20, w4=0.15, w5=0.10
```

Deal Score > 70 = покупать, 50-70 = доп. анализ, < 50 = отклонить.

---

## 9. Composite Scores & Indices

### 9.1 Company Health Index (CHI)

**Концепция**: Единый числовой показатель здоровья компании (0-100).

**Формула**:

```
CHI = Σ (wi × Ni)
```

Где wi — вес категории, Ni — нормализованный балл (0-100) категории.

| Категория | Вес | Метрики внутри | Как нормализовать |
|-----------|-----|----------------|-------------------|
| **Финансовое здоровье** | 25% | Cash Runway, DSCR, Capital Turnover | Runway >6мес=100, <1мес=0 |
| **Операционная эффективность** | 20% | Time-to-Value, Renovation Eff., Pipeline Velocity | В рамках целевых KPI |
| **Инвесторская база** | 20% | NDR, Reinvestment Rate, NPS | NDR>120%=100, <80%=0 |
| **Портфельный риск** | 15% | HHI, Stale Ratio, Top-5 Concentration | HHI<1500=100, >5000=0 |
| **Рыночная позиция** | 10% | DOM vs market, Discount at purchase | |
| **Рост** | 10% | New investors, Pipeline momentum | |

**Пример расчёта**:

```
Финансы: Runway=4мес→67, DSCR=1.5→83, Capital Turnover=0.37→37 → Avg=62 × 0.25 = 15.5
Операции: TTV=6мес→80, Renov=0.95→90, Pipeline=OK→75 → Avg=82 × 0.20 = 16.4
Инвесторы: NDR=105%→75, Reinvest=40%→50, NPS=35→55 → Avg=60 × 0.20 = 12.0
Портфель: HHI=4168→25, Stale=10%→70, Top5=42%→35 → Avg=43 × 0.15 = 6.5
Рынок: DOM=40→80, Discount=30%→90 → Avg=85 × 0.10 = 8.5
Рост: NewInv=+10%→70, Pipeline=1.1→65 → Avg=68 × 0.10 = 6.8

CHI = 15.5 + 16.4 + 12.0 + 6.5 + 8.5 + 6.8 = 65.7 / 100
```

**Интерпретация**:
- 80-100 = отличное состояние
- 60-80 = здоровое, есть зоны роста
- 40-60 = требует внимания
- < 40 = критическое состояние

### 9.2 Advanced Traffic Light System (5-уровневый RAG)

Вместо простого Red/Amber/Green — 5 уровней с чёткими порогами:

```
🟣 EXCEPTIONAL (P95+)  — метрика в топ-5% за всё время
🟢 ON TRACK            — в пределах целевого диапазона
🟡 WATCH               — 80-100% от цели (тренд ухудшается)
🟠 WARNING             — 60-80% от цели (требует плана действий)
🔴 CRITICAL            — < 60% от цели (немедленное действие)
```

**Дополнительные правила**:
1. **Trend-aware**: Если метрика GREEN но тренд нисходящий 3 мес подряд → WATCH
2. **Velocity-based**: Не только текущее значение, но скорость изменения
3. **Context-sensitive**: Стадия объекта влияет на пороги (объект в "ремонте" — DOM не считается)

### 9.3 Deal Quality Score (DQS)

**Формула** (для завершённых объектов, ретроспективно):

```
DQS = 0.35 × IRR_norm + 0.25 × Speed_norm + 0.20 × Predictability + 0.10 × Risk_adj + 0.10 × Size_adj

Где:
- IRR_norm = (IRR объекта - Min IRR) / (Max IRR - Min IRR) × 100
- Speed_norm = (Max срок - Срок объекта) / (Max срок - Min срок) × 100
- Predictability = 100 - |% отклонения от плана| (по доходности)
- Risk_adj = 100 - (доля в портфеле × 10) (штраф за крупные сделки)
- Size_adj = 100 если размер в пределах 1σ от среднего, штраф за outliers
```

---

## 10. Benchmarking

### 10.1 Внутренние бенчмарки (Estate Invest vs Estate Invest)

| Метрика | Текущее (оценка) | Целевое | Top Performers |
|---------|------------------|---------|----------------|
| IRR (средний по объектам) | ~30-50% годовых | > 40% | ИП №40: ~690% |
| MOIC | ~1.15-1.25x | > 1.2x | Зависит от split |
| Time-to-Sale | 3-18 мес | < 8 мес | ИП №40: 18 дней |
| Renovation Efficiency | ~90-95% | > 95% | < 5% overrun |
| Discount at Purchase | ~30-50% | > 30% | |
| Investor Churn | ~5%/квартал | < 3%/квартал | |
| Conversion (показ→сделка) | ~15-25% | > 20% | |

### 10.2 Рыночные бенчмарки (Россия, 2025-2026)

| Метрика | Рынок РФ | Estate Invest | Комментарий |
|---------|----------|---------------|-------------|
| Средняя арендная доходность | 5-7% годовых | 20-40% ROI за сделку | Несравнимо лучше |
| Банковский депозит | 18-21% годовых | ~30-50% IRR | Значительно обгоняет |
| MOEX (фондовый рынок) | ~15-20% годовых | ~30-50% IRR | Обгоняет |
| RE PE фонды (top quartile) | 15-20% Net IRR | ~20-40% Net IRR | На уровне лучших |
| Fix-and-flip (международный) | 10-20% ROI за 4-6 мес | 10-40% за 3-12 мес | Конкурентно |
| Доля аукционных сделок в РФ | 19% от инвестиций в RE | Основная модель | Нишевая специализация |

### 10.3 Kaplan-Schoar PME для Estate Invest

```
Бенчмарк: Банковский депозит 20% годовых

Если Estate Invest IRR = 35% годовых:
KS-PME ≈ 1.35 / 1.20 = 1.125

> 1.0 → Estate Invest обгоняет депозиты на 12.5%
```

```
Бенчмарк: MOEX Index (~18% годовых):
KS-PME ≈ 1.35 / 1.18 = 1.144

> 1.0 → Estate Invest обгоняет рынок акций на 14.4%
```

---

## 11. Cohort Analysis for Investors

### 11.1 Cohort Definition

Группировка инвесторов по дате регистрации (помесячно или поквартально).

```
Когорта Q1-2024: инвесторы, зарегистрированные в январе-марте 2024
Когорта Q2-2024: инвесторы, зарегистрированные в апреле-июне 2024
...
```

### 11.2 Retention Matrix

```
         M+0   M+3   M+6   M+9   M+12  M+18  M+24
Q1-2024  100%  85%   78%   72%   68%   60%   55%
Q2-2024  100%  88%   80%   75%   70%   63%   -
Q3-2024  100%  82%   75%   70%   65%   -     -
Q4-2024  100%  90%   85%   78%   -     -     -
Q1-2025  100%  87%   80%   -     -     -     -
```

**Что искать**:
- Улучшается ли retention у поздних когорт? → Продукт улучшается
- Есть ли "обрыв" на конкретном месяце? → Системная проблема
- Какая когорта лучшая? → Что особенного было в том периоде?

### 11.3 Average Investment Size by Cohort

```
         Первое вложение  Через 6 мес   Через 12 мес  LTV (24 мес)
Q1-2024  85 000           120 000       180 000       450 000
Q2-2024  95 000           140 000       200 000       -
Q3-2024  110 000          155 000       -             -
```

**Тренды**:
- Растёт ли средний чек у новых когорт? → Изменяется аудитория или продукт
- Растёт ли размер довложений? → Инвесторы доверяют больше

### 11.4 Investor Lifetime Value (iLTV)

**Формула**:

```
iLTV = Avg Investment × Avg MOIC × Avg кол-во реинвестиций × GP Share

Или через unit economics:
iLTV = Средний доход компании от одного инвестора за всю жизнь
     = Σ (Вложение × Доходность × 50% GP share) по всем объектам инвестора
```

**Пример**:
- Средний инвестор: 3 сделки за 2 года, средний вклад 100к, средняя доходность 25%
- iLTV = 3 × 100 000 × 0.25 × 0.50 = 37 500 руб доход компании

**CAC (Customer Acquisition Cost)**:

```
CAC = Расходы на привлечение / Кол-во новых инвесторов
```

**LTV/CAC ratio**:
- > 3.0 = здоровый бизнес
- 1.0-3.0 = нужно оптимизировать
- < 1.0 = привлечение дороже пожизненной ценности (убыточно)

### 11.5 Reinvestment by Cohort

```
         % реинвестирующих после 1й сделки  После 2й  После 3й
Q1-2024  65%                                48%       35%
Q2-2024  70%                                52%       -
Q3-2024  72%                                -         -
```

**Улучшение conversion к реинвестированию**: каждый +10% reinvestment rate = значительный рост без затрат на привлечение.

### 11.6 Cohort Revenue Contribution

**Формула**:

```
Cohort Revenue Share = Выручка от когорты / Общая выручка × 100%
```

Если 60% выручки приносят когорты 2+ лет — бизнес стабилен. Если 80% от когорт < 6 мес — бизнес хрупок (зависит от постоянного притока новых инвесторов).

---

## 12. Implementation Roadmap для Estate Invest

### Уровень 1 — Must Have (немедленно)

| Метрика | Источник данных | Сложность |
|---------|----------------|-----------|
| IRR по каждому ИП | Google Sheets (Монитор) + кассы | Средняя |
| MOIC по каждому ИП | Суммы из касс | Простая |
| DPI (общий) | Выплаты / Вложения | Простая |
| Time-to-Sale по объектам | Даты из Монитора | Простая |
| DOM (Days on Market) | Авито API / Скаут | Автоматизируемая |
| Renovation Efficiency | План vs Факт из касс | Простая |
| Investor Churn (quarterly) | CRM Битрикс24 | Средняя |

### Уровень 2 — Should Have (в течение месяца)

| Метрика | Источник данных | Сложность |
|---------|----------------|-----------|
| HHI (география + тип) | Монитор | Простая (формула) |
| Top-5 Concentration | Монитор | Простая |
| Sales Velocity | Авито + CRM | Средняя |
| Pipeline Velocity | Стадии объектов | Средняя |
| NDR (Net Dollar Retention) | Финансовые таблицы | Сложная |
| Reinvestment Rate | Операции (довложения) | Средняя |
| Cash Runway | Финансовые таблицы | Простая |

### Уровень 3 — Nice to Have (квартал)

| Метрика | Источник данных | Сложность |
|---------|----------------|-----------|
| Company Health Index (CHI) | Агрегация уровня 1-2 | Сложная |
| NPS | Опрос через Telegram-бот | Средняя |
| Cohort Analysis | Битрикс24 + Sheets | Сложная |
| iLTV / CAC | Маркетинг + финансы | Сложная |
| PME (vs депозиты/рынок) | IRR + рыночные данные | Средняя |
| J-curve визуализация | IRR по месяцам | Средняя |
| Predictive Deal Score | Исторические данные | Сложная |

### Уровень 4 — Advanced (полугодие)

| Метрика | Источник данных | Сложность |
|---------|----------------|-----------|
| 5-уровневый RAG дашборд | Все метрики | Очень сложная |
| Waterfall модель | Переработка финмодели | Стратегическая |
| Real-time NAV per investor | ЛК + оценки | Очень сложная |
| Auction Market Intelligence | Парсинг торговых площадок | Автоматизируемая |
| Revenue Predictability Score | 12+ мес истории | Средняя |

---

## Источники

### Fund Performance Metrics
- [Private Equity Fund Performance Metrics: TVPI, DPI, IRR](https://breakingintowallstreet.com/kb/financial-sponsors/private-equity-fund-performance-metrics/)
- [Understanding TVPI, DPI, and IRR](https://www.bipventures.vc/news/understanding-tvpi-dpi-and-irr-key-metrics-for-informed-private-capital-investors)
- [Fund Performance Metrics: IRR, DPI, RVPI & TVPI](https://www.qapita.com/blog/fund-metrics-irr-dpi-rvpi-tvpi)
- [Understanding MOIC in Private Equity](https://waveup.com/blog/understanding-moic-in-private-equity/)
- [Multiple on Invested Capital (MOIC)](https://www.moonfare.com/glossary/multiple-on-invested-capital-moic)

### Waterfall Distribution
- [Real Estate Waterfall — Wall Street Prep](https://www.wallstreetprep.com/knowledge/real-estate-waterfall/)
- [Real Estate Equity Waterfall Model](https://www.adventuresincre.com/real-estate-equity-waterfall-model/)
- [GP Catch-Ups with Examples — EisnerAmper](https://www.eisneramper.com/insights/real-estate/waterfall-gp-catch-ups-0123/)

### Gross vs Net Returns
- [Gross IRR vs Net IRR — Transacted](https://www.transacted.io/gross-irr-vs-net-irr)
- [Gross and Net Returns Calculations](https://financetrain.com/gross-and-net-returns-calculations)

### J-Curve
- [The J-Curve in Private Equity Real Estate — CrowdStreet](https://crowdstreet.com/resources/investment-fundamentals/the-j-curve-in-private-equity-real-estate-investments)
- [J-Curve Effect — Wall Street Prep](https://www.wallstreetprep.com/knowledge/j-curve/)
- [J-Curves: An Introduction — Hamilton Lane](https://www.hamiltonlane.com/en-us/knowledge-center/j-curves)

### PME
- [Public Market Equivalent — Carta](https://carta.com/learn/private-funds/management/fund-performance/pme/)
- [Public Market Equivalent — Wikipedia](https://en.wikipedia.org/wiki/Public_Market_Equivalent)
- [A Framework for Benchmarking — Cambridge Associates](https://www.cambridgeassociates.com/insight/a-framework-for-benchmarking/)

### Portfolio Risk & Concentration
- [Herfindahl-Hirschman Index — Corporate Finance Institute](https://corporatefinanceinstitute.com/resources/valuation/herfindahl-hirschman-index-hhi/)
- [Concentration Risk in Angel Investing: HHI Score](https://angelhub.app/blog/concentration-risk-hhi-score-explained)
- [Portfolio Risk Profiling: Focus on Concentration Risk](https://www.debexpert.com/blog/portfolio-risk-profiling-focus-on-concentration-risk)

### Vintage Diversification
- [Importance of Vintage Diversification — CAIS](https://www.caisgroup.com/articles/does-vintage-diversification-matter-in-private-markets)
- [What is Vintage Diversification?](https://www.optoinvest.com/insights/what-is-vintage-diversification)

### Operational Efficiency
- [33 Real Estate Metrics to Track — NetSuite](https://www.netsuite.com/portal/resource/articles/business-strategy/real-estate-metrics.shtml)
- [10 Real Estate KPIs to Track — Plecto](https://www.plecto.com/blog/sales-performance/kpis-for-real-estate/)
- [Sales Velocity 101 — Dock](https://www.dock.us/library/sales-velocity)

### Renovation & Cost Overruns
- [Construction Cost Overrun Statistics — ContiMod](https://www.contimod.com/construction-cost-overrun-statistics/)
- [Construction Cost Overruns — Propeller Aero](https://www.propelleraero.com/blog/10-construction-project-cost-overrun-statistics-you-need-to-hear/)

### Investor Relations
- [LP Portal for Investor Reporting — Zapflow](https://www.zapflow.com/investor-relations/lp-portal-and-reporting)
- [Investor Reporting: From Compliance to Strategy — Carta](https://carta.com/learn/private-funds/management/portfolio-management/investor-reporting/)
- [Investor Relations Essentials — Digify](https://digify.com/blog/calculating-communicating-fund-metrics/)

### NPS & Satisfaction
- [NPS Real Estate — CustomerGauge](https://customergauge.com/benchmarks/blog/nps-real-estate)
- [The State of NPS in PE-Backed Companies](https://www.stonehillinnovation.com/blog/the-state-of-nps-in-private-equity-backed-companies-2025)

### Capital Calls & Deployment
- [What is a Capital Call — Carta](https://carta.com/learn/private-funds/management/capital-calls/)
- [ROCC & MOCC: Optimising Capital Deployment — Klarphos](https://www.klarphos.com/news-insights/rocc-mocc-ii-a-practical-approach-to-optimizing-capital-deployment-in-private-markets)

### Financial Health
- [DSCR in Real Estate — TurboTenant](https://www.turbotenant.com/accounting/debt-service-coverage-ratio-real-estate/)
- [DSCR — JP Morgan](https://www.jpmorgan.com/insights/real-estate/commercial-term-lending/what-is-debt-service-coverage-ratio-dscr-in-real-estate)

### Market Intelligence
- [Real Estate Market Intelligence Dashboard — DataMam](https://datamam.com/real-estate-market-intelligence/)
- [Real Estate Analytics — Altos Research](https://www.altosresearch.com/altos/website/RealEstateMarketAnalytics.page)

### Composite Scoring
- [Composite Financial Index — Barton CC](https://www.bartonccc.edu/planning/kpi-metrics-dashboard/composite-financial-index)
- [How to Calculate KPIs and Create a Scorecard — BSCDesigner](https://bscdesigner.com/calculate-metrics.htm)
- [RAG Status Guide — ClearPoint Strategy](https://www.clearpointstrategy.com/blog/establish-rag-statuses-for-kpis)

### Benchmarking Russia
- [Russia Residential Property Market — Global Property Guide](https://www.globalpropertyguide.com/europe/russia/price-history)
- [Russia Real Estate Investment Market — 6Wresearch](https://www.6wresearch.com/industry-report/russia-real-estate-investment-market)
- [Gross Rental Yields in Russia](https://www.globalpropertyguide.com/europe/russia/rental-yields)

### Cohort Analysis
- [Cohort Analysis for Lifetime Value Estimation — Growth-onomics](https://growth-onomics.com/cohort-analysis-for-lifetime-value-estimation/)
- [Retention Cohort Analysis — WaveUp](https://waveup.com/blog/retention-cohorts-the-best-way-to-integrate-them-into-your-model/)
- [Investor's Guide to Reinvestment Rates — FNRP](https://fnrpusa.com/blog/reinvestment-rates/)

### Fix-and-Flip Benchmarks
- [Fix and Flip Strategy — Primior](https://primior.com/what-is-fix-and-flip-strategy-in-real-estate-investing/)
- [How to Calculate ROI for Flips — DealCheck](https://dealcheck.io/blog/how-to-calculate-return-on-investment-flips/)

### Leading Indicators
- [Predictive Analytics in Real Estate — RTS Labs](https://rtslabs.com/predictive-analytics-real-estate/)
- [Role of Economic Indicators in RE Investment](https://www.ownitdetroit.com/blog/real-estate-investment-the-role-of-economic-indicators)
