# Car Catalog — каталог автомобілів

REST API каталогу автомобілів: марка, модель, рік, ціна, пробіг. Навчальний проєкт з курсу «Професійний Python»,
варіант №5, лабораторні роботи №1–10. Виконав: Біляк Олег, група ФЕП-31.

Можливості:
- пошук за маркою і моделлю, фільтрація за роком, сортування і пагінація;
- найдорожчий автомобіль, середня ціна, автомобіль із мінімальним пробігом (GET /cars/statistics);
- CRUD автомобілів, виробники та їхні автомобілі; асинхронне завантаження групи автомобілів;
- SQLite + SQLAlchemy ORM + Alembic; FastAPI + Pydantic; health check для Docker і моніторингу;
- конфігурація через environment variables, Docker image, CI на GitHub Actions.

Архітектура:

```text
Client ──HTTP──▶ FastAPI (api.py, schemas.py) ──▶ CarCatalogService ──▶ Repository ──▶ SQLAlchemy ──▶ SQLite
                       ▲ settings (config.py ← environment variables / .env)
```

## Встановлення

Потрібен Python 3.11 або новіший.

```bash
python -m venv .venv
source .venv/bin/activate                     # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev,test]"        # пакет + ruff, mypy, build, pytest
python -m pip install -e ".[dev,test,bench]"  # + matplotlib для графіків ЛР9
```

Встановлення готового пакета (wheel) без вихідного коду:

```bash
python -m build                                # dist/car_catalog-<версія>-py3-none-any.whl і .tar.gz
python -m pip install dist/car_catalog-*.whl
car-catalog                                    # запуск сервісу
```

## Конфігурація

Налаштування читаються з environment variables, потім з файлу `.env` у поточному каталозі, інакше —
значення за замовчуванням (config.py, pydantic-settings).

```bash
cp .env.example .env                           # .env не потрапляє в Git (.gitignore)
```

| Змінна | За замовчуванням | Що задає |
|---|---|---|
| APP_NAME | Car Catalog | назва в логах |
| ENVIRONMENT | development | development / test / production; у development Uvicorn перезапускається при зміні коду |
| DATABASE_URL | sqlite:///car_catalog.db | база даних (застосунок і `alembic`) |
| LOG_LEVEL | INFO | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| HOST | 127.0.0.1 | адреса сервера (у Docker — 0.0.0.0) |
| PORT | 8000 | порт сервера |
| SEED_DEMO_DATA | false | true — заповнити ПОРОЖНЮ БД 5 виробниками і 10 автомобілями |
| CAR_CATALOG_API_URL, CAR_CATALOG_HTTP_TIMEOUT, CAR_CATALOG_RETRY_ATTEMPTS, CAR_CATALOG_MAX_CONCURRENCY | http://127.0.0.1:8000, 5.0, 3, 3 | HTTP-клієнт POST /cars/batch (ЛР8) |

Secrets: проєкт не використовує паролів, токенів чи ключів. Якщо БД потребуватиме пароля, він задається лише
змінною DATABASE_URL (у `.env` або в оточенні сервера / GitHub Secrets) і не пишеться в код, README, Dockerfile
чи Git; у логах URL виводиться з прихованим паролем.

## Запуск локально

```bash
car-catalog                                    # або python -m car_catalog.main
```

Сервіс застосовує міграції Alembic до DATABASE_URL, за SEED_DEMO_DATA=true додає демо-дані й запускає Uvicorn:
http://127.0.0.1:8000/docs (Swagger UI), /redoc, /openapi.json, /health.

```bash
export LOG_LEVEL=DEBUG SEED_DEMO_DATA=true     # нові значення без зміни коду
ENVIRONMENT=production PORT=8080 car-catalog
alembic upgrade head                           # міграції вручну (до тієї ж DATABASE_URL)
```

## Docker

```bash
docker build -t car-catalog:1.0.0 .
docker run -d --name car-catalog -p 8000:8000 \
    -v car_catalog_data:/app/data \
    -e SEED_DEMO_DATA=true -e LOG_LEVEL=INFO \
    car-catalog:1.0.0
curl http://127.0.0.1:8000/health              # {"status":"ok","environment":"production",...}
docker ps                                      # STATUS: Up … (healthy)
docker logs car-catalog
docker rm -f car-catalog                       # дані лишаються у volume car_catalog_data
```

Image: multi-stage build (перший етап збирає wheel, другий містить лише встановлений пакет), python:3.12-slim,
користувач appuser (не root), HEALTHCHECK через GET /health, SQLite у volume /app/data
(DATABASE_URL=sqlite:////app/data/car_catalog.db), ENVIRONMENT=production, міграції під час старту.

## REST API

| Метод і шлях | Що робить |
|---|---|
| GET /health | стан сервісу і БД: 200 {"status": "ok", "environment", "version", "database": "ok"} або 503 |
| GET /cars | список; query: brand, model, min_year, max_year, sort_by, descending, limit, offset |
| GET /cars/{car_id} | один автомобіль (404, якщо немає) |
| POST /cars | додати (201; 409 — дублікат VIN; 422 — помилка validation) |
| PATCH /cars/{car_id} | змінити ціну і/або пробіг |
| DELETE /cars/{car_id} | видалити (204) |
| GET /cars/statistics | кількість, середня ціна, найдорожчий, мінімальний пробіг |
| POST /cars/batch | асинхронне завантаження групи автомобілів (HTTPX, Semaphore, retry) |
| GET /manufacturers | виробники |
| GET /manufacturers/{manufacturer_id}/cars | автомобілі виробника |
| GET / | назва, версія, посилання на /docs |

Повна схема: docs/openapi.json (`python -m car_catalog.openapi_export` оновлює файл).

## Тести і якість коду

```bash
python -m pytest -v                            # увесь suite (tests/)
python -m pytest -v --cov --cov-report=term-missing   # coverage, поріг fail_under = 80
python -m ruff check .                         # lint
python -m ruff format --check .                # форматування
python -m mypy                                 # type checking (src, typecheck_demo)
sh check.sh                                    # усе разом, як у CI
```

## CI/CD

GitHub Actions (.github/workflows/ci.yml) запускається на push у main і на pull request:
1. quality-and-tests — Python 3.11 і 3.12 (matrix): ruff check, ruff format --check, mypy, pytest з coverage;
2. build — python -m build, перелік dist, wheel і sdist як artifact car-catalog-dist;
3. docker — docker build і smoke test контейнера (GET /health, GET /cars?brand=BMW).
Jobs build і docker стартують лише після успішних tests.

## Сценарій демонстрації (варіант 5)

```bash
python -m pytest -v && python -m ruff check . && python -m mypy
python -m build && ls dist
docker build -t car-catalog:1.0.0 .
docker run -d --name car-catalog -p 8000:8000 -v car_catalog_data:/app/data -e SEED_DEMO_DATA=true car-catalog:1.0.0
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/cars?brand=Toyota"              # пошук за маркою
curl "http://127.0.0.1:8000/cars?model=Octavia"             # пошук за моделлю
curl "http://127.0.0.1:8000/cars?min_year=2018&max_year=2021"   # фільтр за роком
curl http://127.0.0.1:8000/cars/statistics                  # найдорожчий, середня ціна, мінімальний пробіг
curl http://127.0.0.1:8000/manufacturers/1/cars
# http://127.0.0.1:8000/docs — Swagger UI; GitHub → Actions — зелений pipeline
```

## Демонстрації лабораторних робіт

```bash
python -m car_catalog.performance_demo         # ЛР9: профілювання і оптимізації на 250 000 авто (~30 с)
python -m car_catalog.performance_demo 20000   # те саме на меншому каталозі
python benchmarks/benchmark.py                 # повний benchmark ЛР9 (5 повторів, ~5 хв) → benchmarks/results/*.csv
python benchmarks/plot_results.py              # графіки execution_time.png, speedup.png, time_by_size.png
python -m car_catalog.api_demo                 # ЛР8: сервер Uvicorn + HTTP-запити до всіх endpoints (з кореня)
python -m car_catalog.database_app             # ЛР7: БД міграціями → CRUD → запити → DB-API → транзакції
python -m car_catalog.catalog_app              # ЛР6: import → пошук → фільтр → info service → export
python -m car_catalog.importer.app             # ЛР5: імпорт/експорт за config.yaml, з кореня проєкту
python -m car_catalog.importer.experiments     # експерименти ЛР5 (~10 с)
python -m car_catalog.domain.demo              # ЛР4: ООП-модель каталогу
python -m car_catalog.domain.experiments       # ЛР4: DI vs без DI, inheritance vs composition
python -m car_catalog.stream.demo              # ЛР3: потокова обробка, з кореня проєкту
python -m car_catalog.stream.experiment        # ЛР3: eager vs lazy (~1 хв)
python -m car_catalog.analysis                 # ЛР2: аналіз каталогу
python -m car_catalog.benchmark                # ЛР2: benchmark list vs dict / set
python -m car_catalog.console                  # ЛР1: консольний застосунок; --interactive — меню
python -m pytest experiments -v                # експерименти ЛР6 (частина тестів падає навмисно)
```

## Історія лабораторних робіт

- Лабораторна робота №1 «Організація професійного Python-проєкту та Git» — консольний застосунок (console.py).
- Лабораторна робота №2 «Структури даних та функціональна декомпозиція» — аналіз каталогу автомобілів (analysis.py).
- Лабораторна робота №3 «Ітератори, генератори та потокова обробка даних» — потоковий конвеєр (підпакет stream/).
- Лабораторна робота №4 «Професійне ООП та система типів Python» — ООП-модель каталогу (підпакет domain/).
- Лабораторна робота №5 «Обробка помилок, файли та серіалізація» — надійний імпорт/експорт (підпакет importer/, importer/app.py).
- Лабораторна робота №6 «Автоматизоване тестування Python-програм» — test suite на pytest (tests/), сценарій каталогу (catalog_app.py).
- Лабораторна робота №7 «Робота з базами даних у Python» — SQLite, SQLAlchemy ORM, Repository, Alembic (підпакет persistence/, database_app.py).
- Лабораторна робота №8 «Мережеве та асинхронне програмування. REST API» — FastAPI, Pydantic, HTTPX, asyncio (api.py, schemas.py, external_api.py, api_demo.py).
- Лабораторна робота №9 «Паралельність, багатопроцесність та оптимізація» — профілювання, threads, processes, NumPy, caching (підпакет performance/, benchmarks/, performance_demo.py).
- Лабораторна робота №10 «Production Python: Docker, CI/CD та захист проєкту» — config.py, /health, main.py, packaging, Dockerfile, GitHub Actions.

### Можливості (лабораторна робота №9)
- великий тестовий каталог: generate_cars(250 000) з фіксованим seed 42 (performance/analytics.py); baseline на циклах
  Python: пошук за маркою, фільтр за роком, найдорожчий, мінімальний пробіг, середня ціна, статистика пробігу
  і виробників; CPU-bound задача — залишкова вартість кожного авто через 10 років (120 кроків на авто);
- профілювання (performance/profiling.py): cProfile + pstats (ncalls, tottime, cumtime), tracemalloc (поточна і пікова
  пам'ять), timeit; bottleneck — residual_value() (~98 % часу звіту);
- threads (performance/parallel.py): ThreadPoolExecutor і threading.Thread (start/join); I/O-bound читання 8 файлів
  cars_part_N.csv.gz; race condition на спільному лічильнику і виправлення через Lock;
- processes: ProcessPoolExecutor (map з chunksize) і multiprocessing.Process + Queue;
- NumPy (performance/vectorized.py): стовпці каталогу як масиви, маски, argmax/argmin, bincount для виробників,
  векторизована залишкова вартість; результати збігаються з baseline;
- caching (performance/caching.py): lru_cache статистики марки/виробника, ключ містить version каталогу —
  add / update_price / remove інвалідовують кеш; cache_info, cache_clear;
- benchmark framework (performance/benchmarking.py): повтори perf_counter, mean/median, speedup, CSV;
  benchmarks/benchmark.py — 10 000 / 100 000 / 250 000 авто, 1/2/4/8 workers, 5 повторів,
  результати benchmarks/results/benchmark_results.csv і графіки PNG (benchmarks/plot_results.py).

### Можливості (лабораторна робота №8)
- REST API на FastAPI (api.py) над persistence layer ЛР7, JSON, Pydantic schemas з validation (schemas.py):
  рік 1950–2026, ціна > 0, пробіг >= 0, VIN — 17 символів без I, O, Q;
- endpoints: GET /cars (query: brand, model, min_year, max_year, sort_by, descending, limit, offset), GET /cars/{car_id},
  POST /cars (201), PATCH /cars/{car_id} (ціна і пробіг), DELETE /cars/{car_id} (204), GET /cars/statistics
  (найдорожчий, середня ціна, найменший пробіг), GET /manufacturers, GET /manufacturers/{manufacturer_id}/cars,
  POST /cars/batch (асинхронне завантаження групи), GET /;
- status codes 200, 201, 204, 404, 409 (дублікат VIN), 422, 504; structured error responses {"error", "detail"};
  custom exception handlers; dependency injection (Depends: сесія БД, HTTP client); background task (лог нового авто);
  OpenAPI metadata і Swagger UI (/docs);
- async HTTP client (external_api.py): httpx.AsyncClient, asyncio.create_task + gather, Semaphore (rate limiting),
  retry з exponential backoff (0.2, 0.4, 0.8 с; лише мережеві помилки, timeout і 5xx), httpx timeout і asyncio.wait_for,
  налаштування через змінні середовища; один AsyncClient на весь застосунок (lifespan);
- API tests: TestClient і httpx.AsyncClient + ASGITransport з окремою тестовою БД; mock зовнішнього HTTP service
  через httpx.MockTransport; тест main() зі справжнім сервером Uvicorn.

#### Змінні середовища HTTP-клієнта
| Змінна | За замовчуванням | Що задає |
|---|---|---|
| CAR_CATALOG_DATABASE_URL | sqlite:///car_catalog.db | база даних API |
| CAR_CATALOG_API_URL | http://127.0.0.1:8000 | адреса API для POST /cars/batch |
| CAR_CATALOG_HTTP_TIMEOUT | 5.0 | timeout одного HTTP-запиту, с |
| CAR_CATALOG_RETRY_ATTEMPTS | 3 | кількість спроб |
| CAR_CATALOG_MAX_CONCURRENCY | 3 | ліміт Semaphore |

### Можливості (лабораторна робота №7)
- SQLite database car_catalog.db; таблиці manufacturers і cars (one-to-many): PRIMARY KEY, FOREIGN KEY
  cars.manufacturer_id → manufacturers.id з ON DELETE CASCADE, UNIQUE manufacturers.name і cars.vin,
  CHECK для year (1950–2026), price > 0, mileage >= 0; FOREIGN KEY enforcement (`PRAGMA foreign_keys = ON`);
- SQLAlchemy ORM-моделі Manufacturer і Car з relationship(); engine і Session factory (persistence/database.py);
- Repository Pattern: ManufacturerRepository і CarRepository — CRUD, зміна ціни та пробігу, пошук за маркою,
  фільтр за роком, складний фільтр, сортування, пагінація, JOIN з країною виробника;
- функції ЛР1 через SQL (CarCatalogService): пошук за маркою, фільтр за роком, найдорожчий автомобіль,
  середня ціна (AVG), мінімальний пробіг, COUNT, SUM, статистика за виробниками (GROUP BY);
- Python DB-API (sqlite3): параметризований пошук автомобілів за маркою/виробником (`?`), COUNT за країнами;
- транзакція update_prices_for_manufacturer(): масове оновлення цін виробника, commit або rollback, якщо ціна <= 0,
  автомобіль не знайдено або він іншого виробника; IntegrityError → DatabaseConstraintError;
- міграції Alembic: 0001 — таблиці, 0002 — VIN з UNIQUE index (upgrade і downgrade);
- integration tests з окремою тестовою БД у tmp_path: CRUD, relationship, year filter, aggregates, UNIQUE VIN,
  CHECK, FOREIGN KEY, rollback, DB-API, міграції, main.

### Можливості (лабораторна робота №6)
- test suite на pytest: tests/unit (unit tests) і tests/integration (marker `integration`), спільні fixtures у
  tests/conftest.py (fixture factory `make_car`, fixture із yield, autouse, session scope, fake repository);
- перевіряється за варіантом 5: створення Car і валідація year/price/mileage (boundary та invalid), пошук за маркою
  і моделлю, фільтр за роком, найдорожчий автомобіль, середня ціна (`pytest.approx`), мінімальний пробіг, порожній
  каталог, CSV import, malformed record, JSON export (`tmp_path`), configuration діапазону років/цін і environment
  variables (`monkeypatch`), repository через Mock і fake, external vehicle info service через Mock
  (`return_value`, `side_effect`, `assert_called_once_with`, `assert_not_called`, autospec) і AsyncMock,
  integration flow import → filter → export;
- production code ЛР6: domain/vehicle_info.py (external vehicle info service, sync і async), catalog_flow.py
  (імпорт у domain-каталог, фільтр, export); дефекти, знайдені тестами, виправлено (див. git log);
- coverage з branch coverage, поріг `fail_under = 80` у pyproject.toml, HTML-звіт htmlcov/;
- експерименти (папка experiments/, не входять в основний suite): weak vs strong tests, coverage без assertions,
  branch coverage, Mock vs fake, flaky test, tmp_path isolation, failure path.

### Можливості (лабораторна робота №5)
- поля варіанта: vehicle_id, brand, model, year, price, mileage; перевірка positive ID, brand/model,
  допустимого year (діапазон з config.yaml), price >= 0, mileage >= 0;
- streaming CSV import (csv.DictReader), JSON export, фільтр за діапазоном цін з config.yaml;
- ієрархія винятків ApplicationError → ConfigurationError, DataError → DataImportError,
  RecordValidationError, DataExportError; exception chaining (`raise ... from error`);
- strict mode (`skip_invalid: false`) і tolerant mode (`skip_invalid: true`), статистика valid/invalid/filtered/exported;
- logging у консоль і файл logs/application.log з ротацією (RotatingFileHandler);
- atomic export через тимчасовий файл і `replace()`, власні context managers AtomicWriter і logged_operation;
- підвищена складність (усі 20 пунктів п. 84): єдиний interface Importer для CSV, JSON Lines, JSON і YAML;
  Exporter Protocol; вибір формату за розширенням; окремий error CSV; configurable logging; log rotation;
  nested configuration; environment-variable override; atomic export; backup (.bak); streaming JSON Lines;
  progress statistics; transaction-like context manager; validation policy object; retry; schema version;
  export summary report; gzip; custom JSON encoder;
- експерименти: strict vs tolerant, streaming vs eager (peak memory), exception chaining, atomic output,
  помилки конфігурації.

#### Змінні середовища імпорту (override config.yaml)
| Змінна | Ключ YAML |
|---|---|
| CAR_IMPORT_INPUT | input.path |
| CAR_IMPORT_SKIP_INVALID | processing.skip_invalid |
| CAR_IMPORT_LOG_LEVEL | logging.level |

### Можливості (лабораторна робота №4)
- domain entities: Vehicle (ABC) → Car → ElectricCar, колекція VehicleCatalog (composition, `__len__`,
  `__iter__`, `__getitem__`, `__contains__`), properties з перевіркою (price, age, id);
- immutable value objects Money і Mileage (`frozen=True, slots=True`, `__add__`, `total_ordering`);
- search criteria abstraction: VehicleSpecification і BrandSpecification, ModelSpecification,
  YearRangeSpecification, MaxPriceSpecification, AndSpecification (оператор `&`, `__call__`);
- Protocols (HasId, Describable з `runtime_checkable`, VehicleReader, VehicleWriter, EventLogger);
- generic repository Repository[T] / InMemoryRepository[T] (bound TypeVar), UnitOfWork[T],
  generic QueryService[T], constrained TypeVar `Number` (int, float);
- TypedDict VehiclePayload і factory `vehicle_from_payload`, ієрархія винятків CatalogError;
- application service CatalogService з dependency injection і ручний DI container ServiceContainer;
- статистика: найдорожчий автомобіль, середня ціна, мінімальний пробіг;
- експерименти: service без DI vs з DI, inheritance vs composition;
- статична перевірка mypy (налаштування в pyproject.toml), type-checking experiment у typecheck_demo/.

### Можливості (лабораторна робота №3)
- lazy pipeline: читання файлів (yield from) → очищення → CSV parsing → validation з підрахунком invalid → фільтр
  за маркою та роком → нормалізація марки;
- кілька файлів одним потоком (itertools.chain), batching (islice), перші N записів за умовою;
- статистика за один прохід: кількість, середня ціна, найдорожчий, найменший пробіг;
- streaming average price (itertools.accumulate), groupby за маркою після сортування;
- власний iterator CarIdRange, нескінченний generator ID (itertools.count + islice);
- генератор датасетів на 100 000 / 500 000 / 1 000 000 записів (data/generated/, не комітиться);
- експеримент eager vs lazy: час, peak memory (tracemalloc), time to first result, early termination.

### Можливості (лабораторна робота №2)
- унікальні марки (set), кількість автомобілів кожної марки (Counter);
- середня ціна, найдорожчий автомобіль, автомобіль із найменшим пробігом;
- сортування за ціною та універсальне сортування за будь-яким полем;
- фільтрація за роком, closure-фільтри за ціною й пробігом, універсальний фільтр;
- dict-index за ID, групування за маркою (defaultdict) і вкладене групування марка → рік;
- decorators: measure_time і параметризований log_operation з історією операцій у deque;
- benchmark пошуку list vs dict і перевірки наявності list vs set на 1 000 / 10 000 / 100 000 записів.

## Структура проєкту
```text
src/car_catalog/__init__.py    опис пакета і версія
src/car_catalog/config.py      Settings (pydantic-settings) з environment variables, константи домену (ЛР10)
src/car_catalog/models.py      модель Car (ЛР1)
src/car_catalog/services.py    business logic каталогу (ЛР1)
src/car_catalog/console.py     консоль і меню (ЛР1)
src/car_catalog/data.py        демонстраційні записи автомобілів (ЛР2)
src/car_catalog/processors.py  set, dict-index, фільтрація, групування, Counter (ЛР2)
src/car_catalog/analytics.py   статистика, сортування, *args, **kwargs, closure (ЛР2)
src/car_catalog/decorators.py  measure_time, log_operation, історія в deque (ЛР2)
src/car_catalog/analysis.py    аналіз каталогу (ЛР2)
src/car_catalog/benchmark.py   benchmark пошуку (ЛР2)
src/car_catalog/main.py        production entry point: міграції, демо-дані, Uvicorn (ЛР10)
src/car_catalog/openapi_export.py  експорт OpenAPI schema в docs/openapi.json (ЛР10)
src/car_catalog/performance_demo.py  демонстрація продуктивності (ЛР9)
src/car_catalog/api_demo.py    REST API зі справжнім сервером Uvicorn (ЛР8)
src/car_catalog/performance/   analytics (дані і baseline), profiling, parallel, vectorized, caching,
                               benchmarking (ЛР9)
benchmarks/                    benchmark.py, plot_results.py, results/ — CSV і графіки (ЛР9)
src/car_catalog/api.py         FastAPI application, endpoints, exception handlers, lifespan (ЛР8), /health (ЛР10)
src/car_catalog/schemas.py     Pydantic schemas і validation rules (ЛР8)
src/car_catalog/external_api.py  httpx.AsyncClient, retry, Semaphore, Task/gather, timeout (ЛР8)
src/car_catalog/database_app.py  каталог з БД SQLite (ЛР7)
src/car_catalog/catalog_app.py сценарій каталогу, покритий тестами (ЛР6)
src/car_catalog/catalog_flow.py  import → domain-каталог → export (ЛР6)
src/car_catalog/stream/        readers, parsers, models, filters, transformations, batches,
                               analytics, iterators, generate, pipeline, experiment, demo (ЛР3)
src/car_catalog/domain/        models, value_objects, specifications, protocols, repositories,
                               statistics, dto, exceptions, services, experiments, demo (ЛР4),
                               vehicle_info — external vehicle info service (ЛР6)
src/car_catalog/importer/      exceptions, models, config, logging_config, files, readers,
                               validators, exporters, services, experiments, app (ЛР5)
src/car_catalog/persistence/   database, models, repositories, services, dbapi, exceptions, migrations, seed (ЛР7)
src/car_catalog/migrations/    міграції Alembic 0001, 0002 (ЛР7; у пакеті з ЛР10, тому є у wheel і Docker image)
alembic.ini                    налаштування Alembic для командного рядка (URL — з DATABASE_URL)
car_catalog.db                 робоча БД (створюється під час запуску, не комітиться)
config.yaml                    конфігурація імпорту (ЛР5)
data/vehicles.csv              вхідний CSV варіанта 5 з valid і invalid записами (ЛР5)
data/vehicles_extra.yaml       YAML input (ЛР5)
output/, logs/                 результати імпорту та log (створюються під час запуску, не комітяться)
typecheck_demo/errors.py       type-checking experiment (ЛР4)
check.sh                       ті самі перевірки, що в CI: ruff, ruff format, mypy, pytest + coverage
.github/workflows/ci.yml       GitHub Actions (ЛР10)
Dockerfile, .dockerignore      Docker image (ЛР10)
.env.example                   приклад змінних середовища без секретів (ЛР10)
docs/openapi.json              OpenAPI schema (ЛР10)
LICENSE, CHANGELOG.md          ліцензія MIT і історія версій (ЛР10)
data/cars.csv, data/cars_extra.csv  демонстраційні CSV (з некоректними рядками)
tests/conftest.py              спільні fixtures і FakeVehicleRepository (ЛР6)
tests/unit/                    unit tests: test_config, test_packaging, test_openapi_export (ЛР10); test_profiling, test_parallel, test_vectorized, test_caching,
                               test_benchmarking (ЛР9); test_external_api (ЛР8, httpx.MockTransport); test_models, test_catalog_service, test_validators, test_readers,
                               test_configuration, test_exporters, test_vehicle_info, test_repository_doubles,
                               test_files_and_time (ЛР6); unittest-тести ЛР1–5 (test_services, test_analytics,
                               test_stream, test_domain, test_importer) запускаються тим самим pytest
tests/integration/             test_import_pipeline, test_export_pipeline, test_application_flow (ЛР6);
                               test_repositories, test_database_services, test_dbapi, test_migrations,
                               test_database_app (ЛР7, тестова БД у tmp_path); test_api, test_api_demo (ЛР8); test_performance_demo (ЛР9); test_production (ЛР10)
experiments/                   експерименти ЛР6 з тестуванням
```
