# Каталог автомобілів

Навчальний проєкт з курсу «Професійний Python», варіант №5.
Виконав: Біляк Олег, група ФЕП-31.

- Лабораторна робота №1 «Організація професійного Python-проєкту та Git» — консольний застосунок (console.py).
- Лабораторна робота №2 «Структури даних та функціональна декомпозиція» — аналіз каталогу автомобілів (analysis.py).
- Лабораторна робота №3 «Ітератори, генератори та потокова обробка даних» — потоковий конвеєр (main.py, підпакет stream/).

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
Python 3.11+ (лише стандартна бібліотека)

## Встановлення
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
```

## Запуск
```bash
python -m car_catalog.main                     # потокова обробка (ЛР3), запускати з кореня проєкту
car-catalog                                    # те саме, console script
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
src/car_catalog/main.py        точка входу: потокова обробка (ЛР3)
src/car_catalog/stream/        readers, parsers, models, filters, transformations, batches,
                               analytics, iterators, generate, pipeline, experiment (ЛР3)
data/cars.csv, data/cars_extra.csv  демонстраційні CSV (з некоректними рядками)
tests/test_services.py         unit tests ЛР1
tests/test_analytics.py        unit tests ЛР2
tests/test_stream.py           unit tests ЛР3
```
