# Каталог автомобілів

Навчальний проєкт з курсу «Професійний Python», варіант №5.
Виконав: Біляк Олег, група ФЕП-31.

- Лабораторна робота №1 «Організація професійного Python-проєкту та Git» — консольний застосунок (console.py).
- Лабораторна робота №2 «Структури даних та функціональна декомпозиція» — аналіз каталогу автомобілів (main.py).

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
python -m car_catalog.main                     # аналіз каталогу (ЛР2)
car-catalog                                    # те саме, console script
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
src/car_catalog/main.py        точка входу: аналіз каталогу (ЛР2)
src/car_catalog/benchmark.py   benchmark пошуку (ЛР2)
tests/test_services.py         unit tests ЛР1
tests/test_analytics.py        unit tests ЛР2
```
