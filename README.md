[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/kOqwghv0)

# ML-бот для свинг-трейдинга: бинарная классификация доходности акций

**Полное название:** Прогнозирование направления движения биржевых активов: разработка алгоритмической торговой стратегии.

**Студент:** Аброков Димир Тимурович

**Группа:** БИВ 234


## Оглавление

1. [Описание задачи](#описание-задачи)
2. [Структура репозитория](#структура-репозитория)
3. [Быстрый старт](#быстрый-старт)
4. [Команды разработчика](#команды-разработчика)
5. [Данные](#данные)
6. [Результаты](#результаты)
7. [Отчёт](#отчёт)


## Описание задачи

**Задача:** бинарная классификация направления движения цены акции (или индекса S&P 500) на горизонте `H` дней:
`1` — цена закрытия через `H` дней выше цены закрытия сегодня, `0` — ниже или равна.
Базовый горизонт `H=5` дней (свинг-таймфрейм; см. `analysis.md` §5.3 — на дневном горизонте сигнал утопает в шуме).

Вместо регрессии абсолютной цены модель обучается находить короткие паттерны для свинг-сделок.
Из сырых OHLCV-данных генерируются 9 технических индикаторов (RSI, MACD, скользящие средние,
волатильность и пр.) и 5 макро-фичей (VIX, спред 10Y−3M, доходность DXY). Валидация строится
на `TimeSeriesSplit`, чтобы исключить «заглядывание в будущее».

**Датасет:** исторические котировки 5 тикеров (`^GSPC, AAPL, MSFT, JPM, XOM`) и макро-серий
(`^VIX, ^TNX, ^IRX, DX-Y.NYB`) через [`yfinance`](https://pypi.org/project/yfinance/) за 2010–2024.
Поддерживается **multi-ticker pooled training** — модель учится общим паттернам по 5 активам.

**Целевая метрика:** **Precision** при пороге, подбираемом на val (`trade_freq ≥ 0.15`) — точность
торгового сигнала должна давать матожидание сделки выше комиссий брокера. Итог — бэктест с
position sizing и stop-loss на отложенной тестовой выборке.


## Структура репозитория

```
.
├── data
│   ├── raw                     # Сырые котировки (gitignored)
│   └── processed               # Очищенные/фичеризованные данные (gitignored)
├── models                      # Сохранённые артефакты моделей (gitignored)
├── notebooks
│   ├── previous_exps           # Здесь хранятся прошлые и неудачные эксперименты для итогово отчета
│   ├── 01_eda.ipynb            # Разведочный анализ
│   ├── 02_baseline.ipynb       # Baseline-модель (Logistic Regression)
│   └── 03_experiments.ipynb    # Эксперименты и ablation study
├── presentation                # Презентация к защите
├── report
│   ├── images                  # Изображения для отчёта
│   ├── analysis.md             # Анализ метрик/графиков + план улучшений
│   └── report.md               # Финальный отчёт
├── feature-description.md      # Детальное описание 14 фичей (ТА + макро)
├── src
│   ├── preprocessing.py        # OHLCV + 9 ТА-фичей + 5 макро-фичей + multi-ticker pooling
│   ├── modeling.py             # Утилиты сплита, baseline-модели, метрики
│   ├── models.py               # 5 моделей (LogReg, RF, XGB, LGBM, MLP) + Voting/Stacking
│   ├── transformers.py         # Winsorizer для линейных моделей
│   ├── tuning.py               # Optuna-тюнинг XGBoost + isotonic-калибровка
│   ├── threshold.py            # Подбор порога на val (Precision @ trade_freq)
│   ├── cv.py                   # TimeSeriesSplit CV для оценки стабильности
│   ├── backtest.py             # Бэктест с position sizing + stop-loss
│   └── experiments.py          # End-to-end run_experiment()
├── tests
│   └── test_smoke.py           # Smoke-тесты пайплайна
├── .github/workflows/ci.yml    # Lint + format check + tests
├── .pre-commit-config.yaml     # Хуки pre-commit (ruff + basic checks)
├── .dockerignore
├── .env.example                # Шаблон переменных окружения
├── Dockerfile                  # Python 3.10 + JupyterLab (для ноутбуков)
├── Dockerfile.api              # Образ для API и trainer
├── frontend/Dockerfile         # Multi-stage сборка Next.js
├── docker-compose.yml          # Сервисы api, frontend, trainer (profile train), jupyter (profile jupyter)
├── Makefile                    # Шорткаты команд
├── pyproject.toml              # Конфиги ruff и pytest
├── requirements.txt            # Runtime-зависимости
├── requirements-dev.txt        # Dev-зависимости (линт, тесты, pre-commit)
└── README.md
```


## Быстрый старт

Требуется Python 3.10 + Node.js 20 (для локальной разработки) либо Docker.

### Полный стек в Docker (одна команда)

API (FastAPI :8000), фронтенд (Next.js :3000) и опциональный шаг обучения моделей — через `make up`.

```bash
cp .env.example .env

# Первый запуск — обучить модели и поднять api+frontend
make up TRAIN=1

# Последующие запуски (модели уже в models/) — просто поднять сервисы
make up
```

Открыть:
- Frontend: <http://localhost:3000>
- API + Swagger: <http://localhost:8000/docs>

Кастомные параметры обучения (значения по умолчанию `^GSPC`, 2010-01-01, 2024-12-31):
```bash
TICKER=AAPL START_DATE=2015-01-01 END_DATE=2024-12-31 make up TRAIN=1
```

Управление:
```bash
make logs    # tail логов api + frontend
make down    # остановить контейнеры
```

Внутри: `trainer` — отдельный сервис в profile `train`, запускается через `compose run` синхронно и пишет артефакты в `./models/` (bind-mount). `api` монтирует ту же папку в read-only. `frontend` дергает API через `http://localhost:8000` из браузера (host port mapping).

### JupyterLab в Docker (для ноутбуков)

```bash
make docker-up      # http://localhost:8888
make docker-down
```

### Локальная разработка без Docker

Полностью локальный стек: Python venv для ML/API + Node для фронта.

```bash
git clone <url>
cd hseml-group-project-byevyx

# 1. Python окружение
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate            # Windows
cp .env.example .env
make install-dev                    # runtime + dev-зависимости + pre-commit

# 2. Обучить модели (~1–5 мин, нужно один раз)
make api-train

# 3. В одном терминале — API:
make api-up                         # uvicorn на :8000

# 4. В другом терминале — frontend:
cd frontend
cp .env.local.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                         # http://localhost:3000
```


## Команды разработчика

| Команда          | Действие                                        |
|------------------|--------------------------------------------------|
| `make install`   | установить runtime-зависимости                   |
| `make install-dev` | установить dev-зависимости и pre-commit hooks  |
| `make lint`      | `ruff check` по `src/` и `tests/`                |
| `make format`    | автоформатирование + автофикс                    |
| `make test`      | запуск `pytest`                                  |
| `make precommit` | прогнать все pre-commit хуки по всем файлам      |
| `make up`        | поднять api + frontend в Docker (`TRAIN=1` — сначала обучить модели) |
| `make down`      | остановить api + frontend (и trainer, если есть) |
| `make logs`      | tail логов api + frontend                        |
| `make api-train` | обучить модели локально (без Docker), сохранить в `models/` |
| `make api-up`    | запустить FastAPI локально (без Docker) на :8000 |
| `make docker-up` | поднять JupyterLab в Docker на :8888             |
| `make docker-down` | остановить все контейнеры                      |
| `make clean`     | очистить кеши (`__pycache__`, `.pytest_cache`, `.ruff_cache`) |

Переменные окружения (`.env`): `TICKER`, `START_DATE`, `END_DATE`, `RANDOM_SEED`, `MODEL_DIR`, `DATA_DIR` — см. [`.env.example`](.env.example).


## Данные

- `data/raw/` — исходные котировки и макро-серии, выгруженные через `yfinance` (5 тикеров + 4 макро). Кэшируются в CSV; повторные прогоны идут из кэша (`use_cache=True` по умолчанию).
- `data/processed/` — подготовленные датасеты с техническими индикаторами и целевой переменной.

Файлы данных в git не коммитятся (см. [`.gitignore`](.gitignore)); фиксируется только структура папок.

### Полный список фичей

См. [`feature-description.md`](feature-description.md) для подробного описания каждой фичи (формула, экономический смысл, влияние на target).

| Группа | Фичи | Описание |
|---|---|---|
| **Технические (9)** | `Daily_Return`, `Lag_Return_1`, `RSI_14`, `Price_to_SMA20`, `MACD_Histogram`, `Bollinger_pctB`, `ATR_14`, `Volume_ROC`, `Upper_Shadow_Ratio` | Momentum, mean-reversion, волатильность, объём, свечной паттерн |
| **Макро (5)** | `VIX_Level`, `VIX_Change`, `Yield_Spread` (10Y−3M), `Yield_Spread_Change`, `DXY_Return` | Контекст рынка независимый от тикера: страх/жадность, рецессионный сигнал, доллар |


## Пайплайн

Полный прогон одним вызовом:

```python
from src.experiments import run_experiment

result = run_experiment(
    ticker=["^GSPC", "AAPL", "MSFT", "JPM", "XOM"],  # multi-ticker pooled training
    start="2010-01-01",
    end="2024-12-31",
    target_horizon=5,           # 5-дневный горизонт
    include_macro=True,         # +5 макро-фичей
    tune_xgb=True,              # Optuna-тюнинг на TimeSeriesSplit
    n_trials=30,
    calibrate=True,             # isotonic-калибровка вероятностей
    eval_ticker="^GSPC",        # на каком тикере мерить val/test
    min_trade_freq=0.15,
)
```

Бэктест с position sizing + stop-loss:

```python
from src.backtest import backtest_with_sizing

bt = backtest_with_sizing(
    test_df,
    proba=result.test_proba["XGBoost_tuned_calibrated"],
    threshold=result.thresholds["XGBoost_tuned_calibrated"],
    fee=0.002,
    horizon=5,
    stop_loss=-0.03,
    confidence_scaling=True,    # размер позиции ∝ (proba−threshold)/(1−threshold)
)
```


## Результаты

Бэктест на test 2024 (AAPL), все 5 улучшений против исходного baseline:

| Метрика | Baseline (1d, 9 ТА) | + Macro + 5d + Pooled + Sizing/Stop |
|---|---|---|
| cum_return | −45.23% | **+14.78%** |
| Sharpe | −2.67 | **+1.47** |
| max_drawdown | −45.72% | **−7.83%** |

Подробная таблица по всем моделям и тикерам — в `notebooks/03_experiments.ipynb` (секция 15).


## Отчёт

- [`report/analysis.md`](report/analysis.md) — анализ всех метрик/графиков из ноутбуков и план улучшений.
- [`report/report.md`](report/report.md) — финальный отчёт.


## REST API

Поверх ML-пайплайна поднят сервис на FastAPI (`src/api/`). Подходит для интеграции с фронтом на другом порту — CORS открыт всем origin в dev-режиме.

### Запуск

В Docker (рекомендуется) — см. [Полный стек в Docker](#полный-стек-в-docker-одна-команда): `make up TRAIN=1` поднимает API вместе с фронтом и обучением.

Локально:
```bash
pip install -r requirements.txt
make api-train     # обучает модели и пишет models/*.joblib + models/metadata.json
make api-up        # uvicorn на http://localhost:8000
```

Swagger UI: <http://localhost:8000/docs>.

### Эндпоинты

| Метод | Путь        | Назначение |
|------:|-------------|------------|
| GET   | `/health`   | health-check + статус загрузки реестра моделей |
| GET   | `/models`   | список моделей + threshold/features/val/test метрики |
| POST  | `/predict`  | сигнал на конкретную дату по тикеру |
| POST  | `/backtest` | бэктест по тикеру за период, equity curve + Sharpe + drawdown |

Примеры:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/predict \
  -H 'content-type: application/json' \
  -d '{"ticker":"^GSPC","date":"2024-06-03"}'

curl -X POST http://localhost:8000/backtest \
  -H 'content-type: application/json' \
  -d '{"ticker":"^GSPC","start":"2024-01-01","end":"2024-12-31"}'
```

### CORS

В [`src/api/main.py`](src/api/main.py) подключён `CORSMiddleware` c `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. `allow_credentials=False` — спецификация CORS запрещает совмещать wildcard с credentials. Для прода сузить `allow_origins` до конкретных доменов и при необходимости включить credentials.


## Frontend (KABU 株)

Поверх API поднят Next.js-интерфейс в духе японского трейдингового дашборда эпохи Эдо (бордовый, кармин, чёрный, золото — без фиолетового). Полная документация — в [`frontend/README.md`](frontend/README.md).

В Docker (вместе с API): `make up` — см. выше. Используется production-сборка из [`frontend/Dockerfile`](frontend/Dockerfile).

Локально (dev-режим с hot-reload):
```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
# UI -> http://localhost:3000
```

Фронт использует уже существующие ручки API (`/health`, `/models`, `/predict`, `/backtest`) плюс две тонкие надстройки над тем же пайплайном — `/ohlcv` и `/tickers`. Стек: Next.js 14 (App Router), TypeScript, Tailwind, TradingView `lightweight-charts`, TanStack Query, Zustand.
