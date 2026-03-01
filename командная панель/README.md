# Командная панель Estate Invest — Полное исследование

> Дата: 25.02.2026 | 3 раунда исследований | 9 файлов | 90+ источников

---

## Файлы исследования

### Раунд 1 — Дизайн и технологии
| # | Файл | Содержание |
|---|------|-----------|
| 1 | [01-дизайн-дашборда.md](01-дизайн-дашборда.md) | Layout, цвета, шрифты, KPI-карточки, иконки, микро-взаимодействия, референсы |
| 2 | [02-визуализация-данных.md](02-визуализация-данных.md) | Финансовые метрики, воронки, команда, недвижимость, таблицы, статусы, алерты |
| 3 | [03-css-техники.md](03-css-техники.md) | CSS Grid, переменные, glassmorphism, Fonts, Charts, иконки CDN, HTML-шаблон |

### Раунд 2 — Глубокое погружение
| # | Файл | Содержание |
|---|------|-----------|
| 4 | [04-живые-примеры.md](04-живые-примеры.md) | **27 работающих ссылок** на реальные HTML-дашборды (CodePen, GitHub, демо) |
| 5 | [05-контент-карта.md](05-контент-карта.md) | **PRD для Estate Invest** — 7 KPI, 9 секций, 50 виджетов, источники данных, алерты, drill-down |
| 6 | [06-ux-паттерны.md](06-ux-паттерны.md) | Навигация, когнитивная нагрузка, периоды, skeleton screens, accessibility, мобильные, антипаттерны |
| 7 | [07-premium-эстетика.md](07-premium-эстетика.md) | Noise/grain, glow, aurora-фон, анимация чисел, 3D tilt, психология цвета — с CSS-кодом |

### Раунд 3 — Критика и UX
| # | Файл | Содержание |
|---|------|-----------|
| 8 | [08-критический-разбор.md](08-критический-разбор.md) | **10 проблем** исследования: масштаб, палитры, эффекты, данные, реалистичный план |
| 9 | [09-восприятие-и-удобство.md](09-восприятие-и-удобство.md) | **Eye-tracking**, когнитивная нагрузка (4 чанка не 7), светофор, North Star, actionability, мобильный вид |

---

## Quick Start — Ключевые решения

### Стек (single HTML file, всё через CDN)
- **Шрифты**: Inter + JetBrains Mono (Google Fonts)
- **Иконки**: Lucide Icons
- **Графики**: ApexCharts (встроенная dark тема)
- **Карта**: Leaflet.js (для объектов)
- **Стили**: чистый CSS с custom properties
- **JS**: Vanilla JS

### Палитра "Midnight Indigo"
```
Фон:      #0f172a
Карточки:  rgba(255,255,255,0.05) + backdrop-filter blur(12px)
Текст:     #f1f5f9 / #94a3b8
Акцент:    #6366f1 (индиго)
Успех:     #10b981
Ошибка:    #ef4444
Предупр.:  #f59e0b
```

### Структура дашборда (9 секций)
```
┌─────────┬──────────────────────────────────┐
│         │  Header (фильтры, период)        │
│ Sidebar │──────────────────────────────────│
│  Главная│  KPI KPI KPI KPI KPI KPI KPI    │
│  Объекты│──────────────────────────────────│
│  Инвест.│  [Area Chart ~~~~~~]  [Donut]   │
│  Воронки│──────────────────────────────────│
│  Финансы│  [Воронка продаж ──────────]     │
│  Продажи│──────────────────────────────────│
│  Торги  │  [Таблица объектов / сделок]     │
│  KPI    │                                  │
│  Salebot│                                  │
└─────────┴──────────────────────────────────┘
```

### 7 KPI верхнего уровня
1. Капитал под управлением (~196 млн)
2. Стоимость продажи (~388 млн)
3. Распределённая прибыль (~37 млн)
4. Инвесторы (900+ / ~2000)
5. Объектов в работе (N / 118)
6. Конверсия воронки (37%)
7. Прогресс цели (X / 24 объекта/год)

### Premium-рецепт (чеклист)
- [ ] Тёмный фон + noise-текстура
- [ ] Glassmorphism карточки
- [ ] `font-variant-numeric: tabular-nums`
- [ ] Анимация чисел при появлении
- [ ] Каскадный fadeInUp
- [ ] Многослойные тени + glow на hover
- [ ] Aurora-фон (тонкий)
- [ ] Skeleton shimmer при загрузке

### TOP-5 референсов (живые демо)
1. [Tabler](https://preview.tabler.io/) — layout, KPI
2. [ApexCharts Dark](https://apexcharts.com/javascript-chart-demos/dashboards/dark/) — графики
3. [Soft UI Dashboard](https://demos.creative-tim.com/soft-ui-dashboard/pages/dashboard.html) — gradient стиль
4. [TailAdmin](https://demo.tailadmin.com/) — Tailwind варианты
5. [Bank Dashboard](https://codepen.io/havardob/pen/ExvwGBr) — минималистичный тёмный UI

---

## Источники (80+)

Полный список в каждом файле. Ключевые:
- [Fuselab — Trends 2025](https://fuselabcreative.com/top-dashboard-design-trends-2025/)
- [Muzli — Examples 2026](https://muz.li/blog/best-dashboard-design-examples-inspirations-for-2026/)
- [NN/Group — Vertical Nav](https://www.nngroup.com/articles/vertical-nav/)
- [NN/Group — Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
- [Laws of UX — Miller's Law](https://lawsofux.com/millers-law/)
- [CSS-Tricks — Grainy Gradients](https://css-tricks.com/grainy-gradients/)
- [Josh Comeau — Shadows](https://www.joshwcomeau.com/css/designing-shadows/)
- [ApexCharts](https://apexcharts.com/)
- [Lucide Icons](https://lucide.dev/)
- [Dribbble — Finance Dashboard](https://dribbble.com/tags/finance-dashboard)
- [Dribbble — Real Estate Dashboard](https://dribbble.com/tags/real-estate-dashboard)
