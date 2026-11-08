# Каталог автомобілів

Навчальний проєкт з курсу «Професійний Python», варіант №5.
Виконав: Біляк Олег, група ФЕП-31.

- Лабораторна робота №1 «Організація професійного Python-проєкту та Git» — консольний застосунок (console.py).
- Лабораторна робота №2 «Структури даних та функціональна декомпозиція» — аналіз каталогу автомобілів (analysis.py).
- Лабораторна робота №3 «Ітератори, генератори та потокова обробка даних» — потоковий конвеєр (підпакет stream/).
- Лабораторна робота №4 «Професійне ООП та система типів Python» — ООП-модель каталогу (підпакет domain/).
- Лабораторна робота №5 «Обробка помилок, файли та серіалізація» — надійний імпорт/експорт (підпакет importer/, importer/app.py).
- Лабораторна робота №6 «Автоматизоване тестування Python-програм» — test suite на pytest (tests/), сценарій каталогу (catalog_app.py).
- Лабораторна робота №7 «Робота з базами даних у Python» — SQLite, SQLAlchemy ORM, Repository, Alembic (підпакет persistence/, main.py).

## Можливості (лабораторна робота №7)
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

## Можливості (лабораторна робота №6)
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

## Можливості (лабораторна робота №5)
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

### Змінні середовища (override config.yaml)
| Змінна | Ключ YAML |
|---|---|
| CAR_IMPORT_INPUT | input.path |
| CAR_IMPORT_SKIP_INVALID | processing.skip_invalid |
| CAR_IMPORT_LOG_LEVEL | logging.level |

## Можливості (лабораторна робота №4)
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

## Можливості (лабораторна робота №3)
- lazy pipeline: читання файлів (yield from) → очищення → CSV parsing → validation з підрахунком invalid → фільтр
  за маркою та роком → нормалізація марки;
- кілька файлів одним потоком (itertools.chain), batching (islice), перші N записів за умовою;
- статистика за один прохід: кількість, середня ціна, найдорожчий, найменший пробіг;
- streaming average price (itertools.accumulate), groupby за маркою після сортування;
- власний iterator CarIdRange, нескінченний generator ID (itertools.count + islice);
- генератор датасетів на 100 000 / 500 000 / 1 000 000 записів (data/generated/, не комітиться);
- експеримент eager vs lazy: час, peak memory (tracemalloc), time to first result, early termination.

## Можливості (лабораторна робота №2)
- унікальні марки (set), кількість автомобілів кожної марки (Counter);
- середня ціна, найдорожчий автомобіль, автомобіль із найменшим пробігом;
- сортування за ціною та універсальне сортування за будь-яким полем;
- фільтрація за роком, closure-фільтри за ціною й пробігом, універсальний фільтр;
- dict-index за ID, групування за маркою (defaultdict) і вкладене групування марка → рік;
- decorators: measure_time і параметризований log_operation з історією операцій у deque;
- benchmark пошуку list vs dict і перевірки наявності list vs set на 1 000 / 10 000 / 100 000 записів.

## Вимоги
Python 3.11+, PyYAML, SQLAlchemy 2, Alembic (встановлюються з пакетом); для розробки — mypy і types-PyYAML (`.[dev]`);
для тестів — pytest, pytest-cov, pytest-asyncio (`.[test]`)

## Встановлення
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev,test]"
```

## Запуск
```bash
python -m car_catalog.main                     # ЛР7: БД міграціями → CRUD → запити → DB-API → транзакції (з кореня проєкту)
car-catalog                                    # те саме, console script
alembic upgrade head                           # застосувати міграції до car_catalog.db
alembic current                                # поточна ревізія; alembic history — список міграцій
alembic downgrade -1                           # скасувати останню міграцію (VIN)
sqlite3 car_catalog.db ".schema"               # переглянути схему БД
python -m car_catalog.catalog_app              # сценарій каталогу ЛР6: import → пошук → фільтр → info service → export
python -m car_catalog.importer.app             # імпорт/експорт за config.yaml (ЛР5), з кореня проєкту
python -m car_catalog.importer.app other.yaml  # інший файл конфігурації
CAR_IMPORT_SKIP_INVALID=false python -m car_catalog.importer.app   # strict mode без зміни YAML
python -m car_catalog.importer.experiments     # експерименти ЛР5 (~10 с)
python -m car_catalog.domain.demo              # ООП-модель каталогу (ЛР4)
python -m car_catalog.domain.experiments       # DI vs без DI, inheritance vs composition (ЛР4)
python -m car_catalog.stream.demo              # потокова обробка (ЛР3), запускати з кореня проєкту
python -m car_catalog.stream.experiment        # eager vs lazy, early termination (ЛР3, ~1 хв)
python -m car_catalog.analysis                 # аналіз каталогу (ЛР2)
python -m car_catalog.benchmark                # benchmark list vs dict / set (ЛР2)
python -m car_catalog.console                  # консольний застосунок ЛР1
python -m car_catalog.console --interactive    # меню ЛР1
```

## Тести
```bash
python -m pytest -v                            # увесь suite (tests/)
python -m pytest tests/unit/test_models.py     # один файл
python -m pytest "tests/unit/test_models.py::test_rejects_year_outside_range"   # один test
python -m pytest -m integration                # лише integration tests
python -m pytest tests/integration/test_repositories.py -v   # тести persistence layer (ЛР7)
python -m pytest -m "not integration"          # лише unit tests
python -m pytest -v --cov --cov-branch --cov-report=term-missing --cov-report=html   # coverage, htmlcov/index.html
python -m pytest experiments -v                # експерименти ЛР6 (частина тестів падає навмисно)
```

## Перевірка типів
```bash
python -m mypy                                 # src і typecheck_demo, налаштування в pyproject.toml
sh check.sh                                    # CI-ready команда: mypy + pytest з порогом coverage
```

## Структура проєкту
```text
src/car_catalog/__init__.py    опис пакета і версія
src/car_catalog/config.py      конфігураційні константи
src/car_catalog/models.py      модель Car (ЛР1)
src/car_catalog/services.py    business logic каталогу (ЛР1)
src/car_catalog/console.py     консоль і меню (ЛР1)
src/car_catalog/data.py        демонстраційні записи автомобілів (ЛР2)
src/car_catalog/processors.py  set, dict-index, фільтрація, групування, Counter (ЛР2)
src/car_catalog/analytics.py   статистика, сортування, *args, **kwargs, closure (ЛР2)
src/car_catalog/decorators.py  measure_time, log_operation, історія в deque (ЛР2)
src/car_catalog/analysis.py    аналіз каталогу (ЛР2)
src/car_catalog/benchmark.py   benchmark пошуку (ЛР2)
src/car_catalog/main.py        точка входу: каталог з БД SQLite (ЛР7)
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
alembic.ini, migrations/       налаштування Alembic і міграції 0001, 0002 (ЛР7)
car_catalog.db                 робоча БД (створюється під час запуску, не комітиться)
config.yaml                    конфігурація імпорту (ЛР5)
data/vehicles.csv              вхідний CSV варіанта 5 з valid і invalid записами (ЛР5)
data/vehicles_extra.yaml       YAML input (ЛР5)
output/, logs/                 результати імпорту та log (створюються під час запуску, не комітяться)
typecheck_demo/errors.py       type-checking experiment (ЛР4)
check.sh                       CI-ready перевірка: mypy + pytest + coverage (ЛР4, ЛР6)
data/cars.csv, data/cars_extra.csv  демонстраційні CSV (з некоректними рядками)
tests/conftest.py              спільні fixtures і FakeVehicleRepository (ЛР6)
tests/unit/                    unit tests: test_models, test_catalog_service, test_validators, test_readers,
                               test_configuration, test_exporters, test_vehicle_info, test_repository_doubles,
                               test_files_and_time (ЛР6); unittest-тести ЛР1–5 (test_services, test_analytics,
                               test_stream, test_domain, test_importer) запускаються тим самим pytest
tests/integration/             test_import_pipeline, test_export_pipeline, test_application_flow (ЛР6);
                               test_repositories, test_database_services, test_dbapi, test_migrations,
                               test_database_app (ЛР7, тестова БД у tmp_path)
experiments/                   експерименти ЛР6 з тестуванням
```
