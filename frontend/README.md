# KABU 株 — фронтенд

Next.js 14 (App Router) интерфейс для ML-бота из этого репозитория. Стилистика — «японский торговый дашборд эпохи Эдо»: бордовый, кармин, угольно-чёрный, акценты сусального золота, без фиолетового.

## Стек

- **Next.js 14** + React 18 + TypeScript (strict)
- **Tailwind CSS 3** + кастомная палитра KABU
- **TradingView lightweight-charts** — японские свечи, объёмы, линия прогноза
- **TanStack Query** — все обращения к API
- **Zustand** + persist — стейт + избранное + история прогнозов в `localStorage`
- **html-to-image** — экспорт правой панели в PNG
- **Web Audio API** — короткий звук храмового колокола / тайко по сигналу
- Шрифты: `Inter`, `Noto Sans JP`, `IBM Plex Mono` (через `next/font`)

## Какие ручки API используются

Фронт работает с FastAPI-сервисом из `src/api/`:

| Метод | Путь | Где используется |
|------:|------|------------------|
| GET   | `/health`   | бэдж "модели загружены" в шапке, бэйджи ошибок |
| GET   | `/models`   | подгрузка `default_model` + порога |
| GET   | `/tickers`  | селектор активов в шапке |
| GET   | `/ohlcv?ticker&start&end` | свечной график, индикаторы, мини-цены в избранном |
| POST  | `/predict`  | кнопка «Запустить прогноз» |
| POST  | `/backtest` | блок «Бэктест» с equity curve |

> `/ohlcv` и `/tickers` добавлены тонкими врапперами над уже существующими `load_ohlcv()` и `service.list_supported_tickers()` — модели и пайплайн признаков не меняются, фронт читает ровно те же данные, на которых обучается классификатор.

## Запуск

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
# UI -> http://localhost:3000
```

Параллельно нужно поднять бекенд:

```bash
# из корня репозитория
make api-train     # один раз, чтобы появились models/*.joblib и metadata.json
make api-up        # FastAPI на :8000
```

CORS открыт всем origin (`src/api/main.py`), так что `:3000` ↔ `:8000` работают без прокси.

## Структура

```
frontend/
├── app/
│   ├── layout.tsx          # корневой layout, шрифты, тема
│   ├── providers.tsx       # QueryClient + переключение CSS-темы
│   ├── page.tsx            # главный дашборд (3 колонки + нижний ряд)
│   └── globals.css         # tailwind + washi-текстура, кастомные классы
├── components/
│   ├── header.tsx          # лого 株, селектор тикера, кнопка "Запустить прогноз"
│   ├── ticker-selector.tsx # выпадашка с поиском
│   ├── favorites-panel.tsx # левая панель: избранные активы
│   ├── candle-chart.tsx    # центр: свечи + объёмы + золотая линия прогноза
│   ├── forecast-panel.tsx  # правая панель: синтез + уровни + RSI/MACD/%B + экспорт PNG
│   ├── backtest-panel.tsx  # /backtest c equity sparkline
│   ├── forecast-history.tsx# журнал прогнозов из localStorage
│   ├── shogun-toggle.tsx   # режим Сёгун (агрессивный порог)
│   ├── theme-toggle.tsx    # тёмная (Эдо) / светлая (washi) тема
│   └── ui/                 # Panel, Seal, Gauge — общие atoms
├── lib/
│   ├── api.ts              # типизированный fetch-клиент
│   ├── types.ts            # mirror pydantic-схем бекенда
│   ├── store.ts            # zustand + persist
│   ├── indicators.ts       # уровни, проекция forecast band, dayChange
│   └── utils.ts            # cn(), форматирование чисел/дат
└── public/favicon.svg      # печать с кандзи 株
```

## Ключевые фичи

- **Свечной график** — TradingView lightweight-charts с золотым SMA-20, объёмами и пунктирной линией прогноза ИИ + конусом доверия.
- **Селектор актива** с поиском (`/tickers`) и свободным вводом любого yfinance-тикера.
- **Избранное** с автоматической подгрузкой last close и дневным изменением.
- **Прогноз** через `/predict` с probability, threshold, signal, предупреждениями. Объяснение на естественном языке.
- **Уровни** — поддержка/сопротивление/стоп-лосс из квантилей последних 30 баров.
- **Спидометры** RSI / MACD / Bollinger %B с зонами овер-/прода и перекупленности.
- **Бэктест** через `/backtest` с равновесной кривой (SVG-спарклайн), Sharpe, max DD, trade freq.
- **Режим Сёгун** (将軍) — на клиенте снижает порог сигнала, чтобы получать более агрессивные ↑.
- **История прогнозов** в `localStorage` с каллиграфическими ✓/✗.
- **Темы** — KABU dark (ночь) и Washi paper (бумажный свиток).
- **Экспорт PNG** правой панели одной кнопкой.
- **Звуковое сопровождение** — короткий синтезированный колокол/тайко при сигнале (опц.).

## Команды

```bash
npm run dev        # dev-сервер
npm run build      # продакшн-сборка
npm run start      # запустить продакшн
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
```
