# Каталог автомобілів

Навчальний проєкт з курсу «Професійний Python», варіант №5.
Виконав: Біляк Олег, група ФЕП-31.

- Лабораторна робота №1 «Організація професійного Python-проєкту та Git» — консольний застосунок (console.py).
- Лабораторна робота №2 «Структури даних та функціональна декомпозиція» — аналіз каталогу автомобілів (analysis.py).
- Лабораторна робота №3 «Ітератори, генератори та потокова обробка даних» — потоковий конвеєр (підпакет stream/).
- Лабораторна робота №4 «Професійне ООП та система типів Python» — ООП-модель каталогу (main.py, підпакет domain/).

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
Python 3.11+ (стандартна бібліотека); для розробки — mypy (`pip install -e ".[dev]"`)

## Встановлення
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Запуск
```bash
python -m car_catalog.main                     # ООП-модель каталогу (ЛР4)
car-catalog                                    # те саме, console script
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
python -m unittest discover -s tests -v
```

## Перевірка типів
```bash
python -m mypy                                 # src і typecheck_demo, налаштування в pyproject.toml
sh check.sh                                    # CI-like команда: mypy + unit tests
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
src/car_catalog/main.py        точка входу: демонстрація ООП-моделі (ЛР4)
src/car_catalog/stream/        readers, parsers, models, filters, transformations, batches,
                               analytics, iterators, generate, pipeline, experiment, demo (ЛР3)
src/car_catalog/domain/        models, value_objects, specifications, protocols, repositories,
                               statistics, dto, exceptions, services, experiments (ЛР4)
typecheck_demo/errors.py       type-checking experiment (ЛР4)
check.sh                       CI-like перевірка: mypy + unit tests (ЛР4)
data/cars.csv, data/cars_extra.csv  демонстраційні CSV (з некоректними рядками)
tests/test_services.py         unit tests ЛР1
tests/test_analytics.py        unit tests ЛР2
tests/test_stream.py           unit tests ЛР3
tests/test_domain.py           unit tests ЛР4
```
