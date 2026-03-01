# CSS и фронтенд техники для HTML-дашборда

> Собрано: 25.02.2026. Фокус: pure HTML/CSS/JS, без фреймворков, всё через CDN.

---

## 1. CSS GRID / FLEXBOX LAYOUTS

### Главная раскладка: sidebar + content

```css
.dashboard {
  display: grid;
  grid-template-columns: 260px 1fr;
  grid-template-rows: 64px 1fr;
  grid-template-areas:
    "sidebar header"
    "sidebar main";
  min-height: 100vh;
}
.sidebar { grid-area: sidebar; }
.header  { grid-area: header; }
.main    { grid-area: main; overflow-y: auto; padding: 24px; }

@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
    grid-template-areas: "header" "main";
  }
  .sidebar { display: none; }
}
```

### Grid для KPI-карточек

```css
/* Авто-адаптивная сетка */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}
```

### Grid для графиков (разная ширина)

```css
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}
.chart-wide { grid-column: span 2; }
.chart-tall { grid-row: span 2; }
.chart-full { grid-column: 1 / -1; }
```

### Flexbox для внутренней разметки карточек

```css
.card { display: flex; flex-direction: column; gap: 12px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.card-footer { display: flex; align-items: center; gap: 6px; margin-top: auto; }
```

---

## 2. CSS CUSTOM PROPERTIES — ПОЛНАЯ СИСТЕМА ТЕМИЗАЦИИ

### Палитра "Midnight Indigo" (рекомендуемая)

```css
:root {
  /* === Фон === */
  --bg-primary:    #0a0a0f;
  --bg-secondary:  #12121a;
  --bg-card:       #1a1a2e;
  --bg-card-hover: #1f1f35;
  --bg-elevated:   #252540;
  --bg-input:      #16162a;

  /* === Бордеры === */
  --border-primary:   #2a2a4a;
  --border-secondary: #1e1e38;
  --border-hover:     #3a3a5c;
  --border-focus:     #6366f1;

  /* === Текст === */
  --text-primary:   #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted:     #64748b;

  /* === Акценты === */
  --accent-primary:  #6366f1;
  --accent-hover:    #818cf8;
  --accent-subtle:   rgba(99, 102, 241, 0.12);

  /* === Семантические === */
  --success:         #10b981;
  --success-bg:      rgba(16, 185, 129, 0.12);
  --warning:         #f59e0b;
  --warning-bg:      rgba(245, 158, 11, 0.12);
  --danger:          #ef4444;
  --danger-bg:       rgba(239, 68, 68, 0.12);
  --info:            #3b82f6;
  --info-bg:         rgba(59, 130, 246, 0.12);

  /* === Графики === */
  --chart-1: #6366f1;
  --chart-2: #8b5cf6;
  --chart-3: #06b6d4;
  --chart-4: #10b981;
  --chart-5: #f59e0b;
  --chart-6: #ec4899;
  --chart-grid: rgba(148, 163, 184, 0.08);

  /* === Тени === */
  --shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md:  0 4px 6px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2);
  --shadow-lg:  0 10px 15px rgba(0, 0, 0, 0.3), 0 4px 6px rgba(0, 0, 0, 0.2);
  --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.15);

  /* === Радиусы === */
  --radius-sm:  6px;
  --radius-md:  12px;
  --radius-lg:  16px;
  --radius-xl:  24px;

  /* === Переходы === */
  --transition-fast:   150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow:   350ms cubic-bezier(0.4, 0, 0.2, 1);

  /* === Шрифты === */
  --font-ui:   'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}
```

### Альтернативная: "Ocean Deep"

```css
:root {
  --bg-primary: #030712;  --bg-card: #1e293b;
  --text-primary: #f8fafc; --accent-primary: #38bdf8;
}
```

### Альтернативная: "Obsidian Emerald"

```css
:root {
  --bg-primary: #09090b;  --bg-card: #27272a;
  --text-primary: #fafafa; --accent-primary: #22c55e;
}
```

---

## 3. GLASSMORPHISM И ЭФФЕКТЫ

### Базовый glass

```css
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
```

### Анимированный glass

```css
.glass-card-animated {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card-animated:hover {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  transform: translateY(-4px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.3);
  border-color: rgba(255, 255, 255, 0.15);
}
```

### Градиентный фон (ambient orbs)

```css
body {
  background: var(--bg-primary);
  background-image:
    radial-gradient(at 20% 80%, rgba(99, 102, 241, 0.15) 0, transparent 50%),
    radial-gradient(at 80% 20%, rgba(139, 92, 246, 0.1) 0, transparent 50%),
    radial-gradient(at 50% 50%, rgba(6, 182, 212, 0.05) 0, transparent 50%);
}
```

### Многослойные тени (Josh W. Comeau)

```css
.shadow-dreamy {
  box-shadow:
    0 1px 2px rgba(0,0,0,0.07),
    0 2px 4px rgba(0,0,0,0.07),
    0 4px 8px rgba(0,0,0,0.07),
    0 8px 16px rgba(0,0,0,0.07),
    0 16px 32px rgba(0,0,0,0.07),
    0 32px 64px rgba(0,0,0,0.07);
}
```

### Gradient border

```css
.gradient-border {
  position: relative;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
}
.gradient-border::before {
  content: '';
  position: absolute; inset: 0;
  border-radius: inherit; padding: 1px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
```

### Glow-эффект

```css
.glow-border {
  border: 1px solid rgba(99, 102, 241, 0.3);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.1), inset 0 0 10px rgba(99, 102, 241, 0.05);
}
.glow-border:hover {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.2), inset 0 0 20px rgba(99, 102, 241, 0.1);
}
```

### Performance glassmorphism:
- Blur max **10-15px**
- `transform: translateZ(0)` для GPU
- Не более 5-8 элементов одновременно
- Fallback:
```css
@supports not (backdrop-filter: blur(10px)) {
  .glass-card { background: rgba(26, 26, 46, 0.95); }
}
```

---

## 4. GOOGLE FONTS — ПОДКЛЮЧЕНИЕ

### Inter + JetBrains Mono (рекомендую)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
```

```css
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
}
.value, .number, code {
  font-family: 'JetBrains Mono', monospace;
}
```

### Другие пары

| UI | Данные | Стиль |
|----|--------|-------|
| Inter | JetBrains Mono | Универсальный |
| Manrope | JetBrains Mono | Fintech |
| DM Sans | DM Mono | Гармоничный |
| Plus Jakarta Sans | JetBrains Mono | Стартап |
| Outfit | Space Mono | Футуристичный |

---

## 5. БИБЛИОТЕКИ ГРАФИКОВ (CDN)

### Chart.js 4

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
```

```javascript
// Глобальные настройки для тёмной темы
Chart.defaults.backgroundColor = 'rgba(99, 102, 241, 0.1)';
Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.08)';
Chart.defaults.color = '#94a3b8';

new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн'],
    datasets: [{
      label: 'Доход',
      data: [12000, 19000, 15000, 25000, 22000, 30000],
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99, 102, 241, 0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHitRadius: 20,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
      }
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#64748b' }, border: { display: false } },
      y: { grid: { color: 'rgba(148, 163, 184, 0.08)' }, ticks: { color: '#64748b' }, border: { display: false } }
    },
  }
});
```

### ApexCharts (более продвинутый)

```html
<script src="https://cdn.jsdelivr.net/npm/apexcharts@3.49.0/dist/apexcharts.min.js"></script>
```

```javascript
new ApexCharts(document.querySelector('#chart'), {
  chart: { type: 'area', height: 350, background: 'transparent', toolbar: { show: false }, fontFamily: 'Inter' },
  theme: { mode: 'dark' },
  colors: ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981'],
  series: [{ name: 'Доход', data: [31, 40, 28, 51, 42, 109, 100] }],
  stroke: { curve: 'smooth', width: 2 },
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.3, opacityTo: 0.05 } },
  grid: { borderColor: 'rgba(148, 163, 184, 0.08)', strokeDashArray: 4 },
  tooltip: { theme: 'dark' },
}).render();
```

### Легковесные альтернативы

```html
<!-- uPlot — ~35KB, самый быстрый для time-series -->
<script src="https://cdn.jsdelivr.net/npm/uplot@1.6.31/dist/uPlot.iife.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/uplot@1.6.31/dist/uPlot.min.css">

<!-- Lightweight Charts (TradingView) — ~45KB, финансовые графики -->
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
```

---

## 6. ИКОНКИ ЧЕРЕЗ CDN

### Lucide (рекомендую)

```html
<script src="https://unpkg.com/lucide@latest"></script>
<i data-lucide="trending-up"></i>
<i data-lucide="users"></i>
<i data-lucide="dollar-sign"></i>
<script>lucide.createIcons();</script>
```

```css
[data-lucide] { width: 20px; height: 20px; stroke: var(--text-secondary); stroke-width: 1.75; }
```

### Phosphor (6 стилей)

```html
<script src="https://unpkg.com/@phosphor-icons/web@2.1"></script>
<i class="ph ph-chart-line-up"></i>
<i class="ph-bold ph-currency-dollar"></i>
```

### Tabler (5900+ иконок)

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css">
<i class="ti ti-chart-bar"></i>
```

---

## 7. АНИМАЦИИ И ПЕРЕХОДЫ

### Hover карточек

```css
.card {
  transition: transform var(--transition-slow), box-shadow var(--transition-slow);
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}
```

### Shine-эффект (блик)

```css
.card-shine { position: relative; overflow: hidden; }
.card-shine::after {
  content: '';
  position: absolute; top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: linear-gradient(to right, transparent 0%, rgba(255,255,255,0.03) 45%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.03) 55%, transparent 100%);
  transform: rotate(30deg) translateX(-100%);
  transition: transform 0.6s ease;
}
.card-shine:hover::after { transform: rotate(30deg) translateX(100%); }
```

### Fade-in при загрузке

```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.card { animation: fadeInUp 0.5s ease forwards; opacity: 0; }
.card:nth-child(1) { animation-delay: 0.0s; }
.card:nth-child(2) { animation-delay: 0.1s; }
.card:nth-child(3) { animation-delay: 0.2s; }
.card:nth-child(4) { animation-delay: 0.3s; }
```

### Count-up числа (Vanilla JS)

```javascript
function animateValue(element, start, end, duration) {
  const startTime = performance.now();
  const range = end - start;
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    element.textContent = Math.floor(start + range * eased).toLocaleString('ru-RU');
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// Запуск при появлении в viewport
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = entry.target;
      animateValue(el, 0, parseInt(el.dataset.target), 2000);
      observer.unobserve(el);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-target]').forEach(el => observer.observe(el));
```

```html
<span class="kpi-value" data-target="12458">0</span>
```

### Пульсация для "live" индикаторов

```css
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); animation: pulse 2s infinite; }

@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
.live-indicator::after {
  content: ''; position: absolute; inset: 0;
  border-radius: 50%; background: var(--success);
  animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
}
```

---

## 8. КАСТОМНЫЕ СКРОЛЛБАРЫ

```css
/* Webkit (Chrome, Edge, Safari) */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: 4px; }
::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 4px; border: 2px solid var(--bg-secondary); }
::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }

/* Тонкий внутри карточек */
.card-content::-webkit-scrollbar { width: 4px; }
.card-content::-webkit-scrollbar-thumb { background: rgba(148, 163, 184, 0.2); border-radius: 2px; }

/* Firefox */
* { scrollbar-width: thin; scrollbar-color: var(--border-primary) var(--bg-secondary); }

html { color-scheme: dark; }
```

---

## 9. CONTAINER QUERIES

```css
.card-wrapper { container-type: inline-size; container-name: card; }

@container card (min-width: 400px) {
  .card-inner { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
}

@container card (max-width: 399px) {
  .card-inner { display: flex; flex-direction: column; gap: 8px; }
  .card-inner .chart { display: none; }
}
```

### Современные CSS-утилиты

```css
/* clamp() для адаптивной типографики */
h1 { font-size: clamp(1.5rem, 2vw + 1rem, 2.5rem); }

/* :has() — стилизация parent */
.card:has(.badge-danger) { border-color: var(--danger-border); }
```

---

## 10. ПОЛНЫЙ HTML-ШАБЛОН (СКЕЛЕТ)

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Командная панель — Estate Invest</title>

  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

  <!-- Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>

  <!-- Charts -->
  <script src="https://cdn.jsdelivr.net/npm/apexcharts@3.49.0/dist/apexcharts.min.js"></script>

  <style>
    /* CSS custom properties + все стили из этого файла */
  </style>
</head>
<body>
  <div class="dashboard">
    <aside class="sidebar glass-card"><!-- навигация --></aside>
    <header class="header"><!-- фильтры, период --></header>
    <main class="main">
      <section class="kpi-grid">
        <div class="card glass-card-animated">
          <div class="card-header">
            <span class="kpi-label">Доход</span>
            <i data-lucide="trending-up"></i>
          </div>
          <span class="kpi-value" data-target="196000000">0</span>
          <div class="card-footer">
            <span class="badge badge--active">+12.5%</span>
            <span class="small-text">vs прошлый месяц</span>
          </div>
        </div>
        <!-- ещё карточки -->
      </section>

      <section class="charts-grid">
        <div class="card glass-card chart-wide">
          <div id="revenueChart"></div>
        </div>
        <div class="card glass-card">
          <div id="funnelChart"></div>
        </div>
      </section>

      <section class="card glass-card chart-full">
        <table class="data-table"><!-- таблица --></table>
      </section>
    </main>
  </div>

  <script>
    lucide.createIcons();
    // Инициализация графиков и count-up
  </script>
</body>
</html>
```

---

## Источники

- [Glassmorphism Dashboard (DEV Community)](https://dev.to/chaitanya_chopde_dd0642ed/build-a-stunning-glassmorphism-dashboard-with-html-css-no-js-needed-292j)
- [Dark Glassmorphism 2026 (Medium)](https://medium.com/@developer_89726/dark-glassmorphism-the-aesthetic-that-will-define-ui-in-2026-93aa4153088f)
- [Designing Beautiful Shadows (Josh W. Comeau)](https://www.joshwcomeau.com/css/designing-shadows/)
- [Animating Number Counters (CSS-Tricks)](https://css-tricks.com/animating-number-counters/)
- [ApexCharts Dark Dashboard (GitHub)](https://github.com/apexcharts/apexcharts.js)
- [CSS Container Queries (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_queries)
- [Custom Scrollbars (Ishadeed)](https://ishadeed.com/article/custom-scrollbars-css/)
- [Lucide Icons](https://lucide.dev/)
- [Phosphor Icons](https://phosphoricons.com/)
- [Tabler Icons](https://tabler.io/icons)
- [Inter Font (Google Fonts)](https://fonts.google.com/specimen/Inter)
- [JetBrains Mono Font Pairings](https://maxibestof.one/typefaces/jetbrains-mono)
