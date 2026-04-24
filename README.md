[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/kOqwghv0)

# ML-бот для свинг-трейдинга: бинарная классификация доходности акций

**Полное название:** Прогнозирование направления движения биржевых активов: разработка алгоритмической торговой стратегии.

**Студенты:** [ФИО / Student IDs]

**Группа:** [Группа]


## Оглавление

1. [Описание задачи](#описание-задачи)
2. [Структура репозитория](#структура-репозитория)
3. [Быстрый старт](#быстрый-старт)
4. [Команды разработчика](#команды-разработчика)
5. [Данные](#данные)
6. [Результаты](#результаты)
7. [Отчёт](#отчёт)


## Описание задачи

**Задача:** бинарная классификация направления дневного движения цены акции (или индекса S&P 500):
`1` — цена закрытия следующего торгового дня выше цены закрытия сегодня, `0` — ниже или равна.

Вместо регрессии абсолютной цены модель обучается находить короткие паттерны для свинг-сделок.
На основе сырых OHLCV-данных методами Feature Engineering генерируются технические индикаторы
(RSI, MACD, скользящие средние, волатильность и пр.). Валидация строится на `TimeSeriesSplit`,
чтобы исключить «заглядывание в будущее».

**Датасет:** исторические котировки, скачиваемые через [`yfinance`](https://pypi.org/project/yfinance/).

**Целевая метрика:** **Precision** при заданном пороге срабатывания — точность торгового сигнала
должна обеспечивать математическое ожидание сделки выше комиссий брокера. Итог — бэктест
стратегии на отложенной тестовой выборке.


## Структура репозитория

```
.
├── data
│   ├── raw                     # Сырые котировки (gitignored)
│   └── processed               # Очищенные/фичеризованные данные (gitignored)
├── models                      # Сохранённые артефакты моделей (gitignored)
├── notebooks
│   ├── 01_eda.ipynb            # Разведочный анализ
│   ├── 02_baseline.ipynb       # Baseline-модель (Logistic Regression)
│   └── 03_experiments.ipynb    # Эксперименты и ablation study
├── presentation                # Презентация к защите
├── report
│   ├── images                  # Изображения для отчёта
│   └── report.md               # Финальный отчёт
├── src
│   ├── preprocessing.py        # Загрузка и обработка данных, фичеринжиниринг
│   └── modeling.py             # Обучение, оценка, бэктест
├── tests
│   └── test_smoke.py           # Smoke-тесты пайплайна
├── .github/workflows/ci.yml    # Lint + format check + tests
├── .pre-commit-config.yaml     # Хуки pre-commit (ruff + basic checks)
├── .dockerignore
├── .env.example                # Шаблон переменных окружения
├── Dockerfile                  # Python 3.10 + JupyterLab
├── docker-compose.yml          # Сервис jupyter на :8888
├── Makefile                    # Шорткаты команд
├── pyproject.toml              # Конфиги ruff и pytest
├── requirements.txt            # Runtime-зависимости
├── requirements-dev.txt        # Dev-зависимости (линт, тесты, pre-commit)
└── README.md
```


## Быстрый старт

Требуется Python 3.10 либо Docker.

### Вариант 1 — Docker (рекомендуется)

```bash
cp .env.example .env
make docker-build
make docker-up
# JupyterLab -> http://localhost:8888
```

### Вариант 2 — локальное окружение

```bash
git clone <url>
cd hseml-group-project-byevyx

python3.10 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate            # Windows

cp .env.example .env
make install-dev                    # зависимости + pre-commit hooks
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
| `make docker-up` | поднять JupyterLab в Docker                      |
| `make docker-down` | остановить контейнеры                          |
| `make clean`     | очистить кеши (`__pycache__`, `.pytest_cache`, `.ruff_cache`) |

Переменные окружения (`.env`): `TICKER`, `START_DATE`, `END_DATE`, `RANDOM_SEED`, `MODEL_DIR`, `DATA_DIR` — см. [`.env.example`](.env.example).


## Данные

- `data/raw/` — исходные котировки, выгруженные через `yfinance`
- `data/processed/` — подготовленные датасеты с техническими индикаторами и целевой переменной

Файлы данных в git не коммитятся (см. [`.gitignore`](.gitignore)); фиксируется только структура папок.


## Результаты

| Модель          | Precision | ROC-AUC | Примечание |
|-----------------|-----------|---------|------------|
| Baseline (LogReg) | —       | —       | OHLCV без фич |
| Лучшая модель   | —         | —       |            |


## Отчёт

Финальный отчёт: [`report/report.md`](report/report.md).
