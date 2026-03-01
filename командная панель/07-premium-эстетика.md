# Premium-эстетика дашборда — CSS-сниппеты и техники

> Собрано: 25.02.2026. Что делает дашборд "wow" — с готовым кодом.

---

## 1. ЗЕРНИСТОСТЬ (NOISE/GRAIN)

Делает интерфейс "осязаемым", не стерильным. SVG feTurbulence — без внешних файлов.

```css
.card {
  position: relative;
  overflow: hidden;
}
.card::before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'%3E%3Cfilter id='a'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23a)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 182px;
  opacity: 0.12;
  pointer-events: none;
  z-index: 1;
}
.card > * { position: relative; z-index: 2; }
```

Настройки: `baseFrequency` 0.5-0.8, `opacity` 0.08-0.15.

---

## 2. СВЕЧЕНИЕ (GLOW)

```css
/* Мягкий glow карточки */
.card-glow {
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.05),
    0 4px 6px rgba(0,0,0,0.3),
    0 0 40px rgba(59,130,246,0.06);
}
.card-glow:hover {
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.1),
    0 8px 25px rgba(0,0,0,0.4),
    0 0 60px rgba(59,130,246,0.15);
}

/* Glow-линия под заголовком */
.heading-glow::after {
  content: "";
  position: absolute;
  bottom: -4px; left: 0;
  width: 60px; height: 2px;
  background: linear-gradient(90deg, #3b82f6, transparent);
  box-shadow: 0 0 12px rgba(59,130,246,0.5);
}

/* Пульсирующий статус */
.status-active {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 6px #22c55e, 0 0 12px rgba(34,197,94,0.4);
  animation: pulse-glow 2s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 6px #22c55e, 0 0 12px rgba(34,197,94,0.4); }
  50% { box-shadow: 0 0 10px #22c55e, 0 0 20px rgba(34,197,94,0.6); }
}
```

---

## 3. AURORA-ФОН (анимированный)

### Движущиеся блобы (чистый CSS)

```css
.aurora-bg {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: #0f0f23;
  overflow: hidden;
  z-index: -1;
}
.aurora-bg .blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  will-change: transform;
}
.blob-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, #1e3a5f, transparent);
  animation: float-1 20s ease-in-out infinite;
}
.blob-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #1a2744, transparent);
  animation: float-2 25s ease-in-out infinite;
}
.blob-3 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #2d1b4e, transparent);
  animation: float-3 18s ease-in-out infinite;
}
@keyframes float-1 {
  0% { transform: translate(10vw, 10vh); }
  33% { transform: translate(60vw, 30vh); }
  66% { transform: translate(30vw, 60vh); }
  100% { transform: translate(10vw, 10vh); }
}
@keyframes float-2 {
  0% { transform: translate(70vw, 60vh); }
  33% { transform: translate(20vw, 20vh); }
  66% { transform: translate(80vw, 40vh); }
  100% { transform: translate(70vw, 60vh); }
}
@keyframes float-3 {
  0% { transform: translate(40vw, 80vh); }
  33% { transform: translate(70vw, 10vh); }
  66% { transform: translate(10vw, 50vh); }
  100% { transform: translate(40vw, 80vh); }
}
```

### Простой анимированный градиент

```css
.animated-gradient-bg {
  background: linear-gradient(-45deg, #0f172a, #1e1b4b, #172554, #1e293b);
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
```

**Правило**: aurora ПРЕДЕЛЬНО тонкая, opacity 0.3-0.5 max. Контент поверх — легко читаем.

---

## 4. АНИМАЦИЯ ЧИСЕЛ

### JavaScript (кроссбраузерный)

```javascript
function animateNumber(element, target, duration = 1500, prefix = '', suffix = '') {
  const startTime = performance.now();
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 4);  // easeOutQuart
    const current = Math.round(target * eased);
    element.textContent = prefix + current.toLocaleString('ru-RU') + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// Запуск при появлении в viewport
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = entry.target;
      animateNumber(el, parseInt(el.dataset.target), 2000);
      observer.unobserve(el);
    }
  });
}, { threshold: 0.1 });
document.querySelectorAll('[data-target]').forEach(el => observer.observe(el));
```

---

## 5. ТИПОГРАФИКА PREMIUM

```css
body {
  font-family: 'Inter', -apple-system, sans-serif;
  font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.metric-value {
  font-variant-numeric: tabular-nums;  /* КРИТИЧНО */
  font-weight: 600;
  font-size: clamp(1.5rem, 4vw, 2.5rem);
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.label {
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.5);
}
```

**Ключевое**: `tabular-nums` — числа одинаковой ширины, не прыгают при обновлении.

---

## 6. МИКРО-АНИМАЦИИ

### Skeleton Shimmer

```css
.skeleton {
  background: linear-gradient(90deg,
    rgba(255,255,255,0.04) 0%,
    rgba(255,255,255,0.08) 50%,
    rgba(255,255,255,0.04) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### Каскадное появление

```css
.card {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.6s ease forwards;
}
.card:nth-child(1) { animation-delay: 0.0s; }
.card:nth-child(2) { animation-delay: 0.1s; }
.card:nth-child(3) { animation-delay: 0.2s; }
.card:nth-child(4) { animation-delay: 0.3s; }

@keyframes fadeInUp {
  to { opacity: 1; transform: translateY(0); }
}
```

### Кольцо прогресса (SVG)

```html
<svg width="60" height="60" viewBox="0 0 60 60">
  <circle cx="30" cy="30" r="25" fill="none"
    stroke="rgba(255,255,255,0.1)" stroke-width="4"/>
  <circle cx="30" cy="30" r="25" fill="none"
    stroke="#3b82f6" stroke-width="4"
    stroke-linecap="round"
    stroke-dasharray="157"
    stroke-dashoffset="47"
    transform="rotate(-90 30 30)"
    style="transition: stroke-dashoffset 1s ease"/>
</svg>
```

`dashoffset = 157 * (1 - progress)`. 70% = 157 * 0.3 = 47.

### Tooltip

```css
.tooltip {
  position: absolute;
  background: rgba(15,23,42,0.95);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 8px 12px;
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 0.2s, transform 0.2s;
  pointer-events: none;
}
.has-tooltip:hover .tooltip {
  opacity: 1;
  transform: translateY(0);
}
```

### SVG-график "рисующий себя"

```css
.chart-line {
  stroke-dasharray: 1000;
  stroke-dashoffset: 1000;
  animation: drawLine 2s ease forwards;
}
@keyframes drawLine {
  to { stroke-dashoffset: 0; }
}
```

---

## 7. ЦВЕТОВАЯ ПСИХОЛОГИЯ

### Почему тёмный = "профессионально"

- Тёмный ассоциируется с концентрацией и утончённостью
- Усиливает яркость цветовых акцентов
- Психологически: контроль, авторитет, эксклюзивность

### Палитра и влияние

```css
:root {
  --bg-primary: #0f172a;     /* глубокий, НЕ мёртвый */
  --text-primary: #f1f5f9;   /* НЕ чистый белый */
  --blue: #3b82f6;           /* доверие, стабильность */
  --emerald: #10b981;        /* рост, прибыль */
  --amber: #f59e0b;          /* внимание */
  --rose: #f43f5e;           /* убыток, срочность */
  --violet: #8b5cf6;         /* премиальность */
}
```

- 42% ассоциируют синий с надёжностью — обязательный акцент для финансов
- `#0f172a`, а не `#000` — чистый чёрный "мёртвый"
- Зелёный ТОЛЬКО для позитивного, красный ТОЛЬКО для негативного

---

## 8. 3D TILT НА HOVER

```javascript
function init3DTilt(selector, threshold = 8) {
  document.querySelectorAll(selector).forEach(card => {
    card.style.transition = 'transform 0.1s ease';
    card.style.transformStyle = 'preserve-3d';
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      const rotateY = (threshold/2 - x * threshold).toFixed(2);
      const rotateX = (y * threshold - threshold/2).toFixed(2);
      card.style.transform = `perspective(${rect.width}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02,1.02,1.02)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1,1,1)';
    });
  });
}
// init3DTilt('.card', 8);  // threshold 5-8 для бизнеса
```

**Threshold 5-8 градусов** — больше 10 выглядит как игрушка.

```css
@media (prefers-reduced-motion: reduce) {
  .card { transform: none !important; }
}
```

---

## 9. ПОЧЕМУ STRIPE / LINEAR / VERCEL PREMIUM

### Общие паттерны

| Паттерн | Как |
|---------|-----|
| Белое пространство | padding 24-32px, gap 16-24px |
| Бордеры | 1px solid rgba(255,255,255,0.06) |
| Радиусы | 8-16px, единообразно |
| Тени | многослойные, 2-3 уровня |
| Анимации | 150-300ms, ease-out |
| Шрифт | Inter, weight 400/500/600 |
| Числа | tabular-nums |
| Иконки | stroke-width 1.5px |

**Stripe**: максимум 2-3 акцента + spring-анимации при drag
**Linear**: ВСЁ за 50мс, клавиатурные шорткаты, "до последнего пикселя"
**Vercel**: монохромность, геометрическая сетка кратно 4px

---

## РЕЦЕПТ PREMIUM (чеклист)

### Must-have (максимум эффекта, минимум кода)

- [ ] Тёмный фон `#0f172a` + текст `#f1f5f9`
- [ ] Noise-оверлей через SVG (opacity 0.1)
- [ ] `font-variant-numeric: tabular-nums`
- [ ] Glassmorphism: `backdrop-filter: blur(12px)` + полупрозрачный фон
- [ ] Многослойные тени (3 уровня) + glow на hover
- [ ] Каскадный fadeInUp при загрузке
- [ ] Анимация чисел при появлении
- [ ] 1px бордеры opacity 0.05-0.1, radius 12-16px

### Nice-to-have

- [ ] Aurora-фон (тонкий, opacity 0.3)
- [ ] 3D tilt карточек (threshold 5-8)
- [ ] SVG progress rings
- [ ] Skeleton shimmer при загрузке
- [ ] Линейный график с draw-in
- [ ] Fluid типографика через `clamp()`

---

## Источники

- [Grainy Gradients — CSS-Tricks](https://css-tricks.com/grainy-gradients/)
- [Aurora Effect — DEV](https://dev.to/oobleck/css-aurora-effect-569n)
- [Animating Counters — CSS-Tricks](https://css-tricks.com/animating-number-counters/)
- [Progress Ring — CSS-Tricks](https://css-tricks.com/building-progress-ring-quickly/)
- [SVG Line Animation — CSS-Tricks](https://css-tricks.com/svg-line-animation-works/)
- [Dark Mode Psychology — Gapsy](https://gapsystudio.com/blog/dark-mode-ux/)
- [3D Hover Effect — LetsBuildUI](https://www.letsbuildui.dev/articles/a-3d-hover-effect-using-css-transforms/)
- [Glassmorphism — Glass UI](https://ui.glass/generator/)
- [Stripe Design — SaaSFrame](https://www.saasframe.io/examples/stripe-payments-dashboard)
- [Linear Case Study — Eleken](https://www.eleken.co/blog-posts/linear-app-case-study)
