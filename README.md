# Каталог автомобілів

Навчальний проєкт з курсу «Професійний Python».
Лабораторна робота №1 «Організація професійного Python-проєкту та Git», варіант №5.
Виконав: Біляк Олег, група ФЕП-31.

## Можливості
- каталог автомобілів: марка, модель, рік, ціна, пробіг;
- пошук за маркою (без урахування регістру);
- фільтрація за роком (від / до);
- найдорожчий автомобіль і автомобіль із найменшим пробігом;
- середня ціна (власний виняток EmptyCatalogError для порожнього каталогу);
- пошук за кількома критеріями (марка, рік від, ціна до) і сортування за ціною;
- консольне меню з введенням і перевіркою даних (`--interactive`).

## Вимоги
Python 3.11+

## Встановлення
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
```

## Запуск
```bash
python -m car_catalog.main                  # демонстраційний сценарій
python -m car_catalog.main --interactive    # консольне меню
car-catalog                                 # console script
```

Приклад запуску:
```text
$ python -m car_catalog.main
=== Каталог автомобілів (варіант 5) ===
...
Найдорожчий автомобіль:
BMW         X5       2020   1890000.00 грн    54000 км

Середня ціна: 793333.33 грн
```

## Тести
```bash
python -m unittest discover -s tests -v
```

## Структура проєкту
```text
src/car_catalog/__init__.py   опис пакета і версія
src/car_catalog/config.py     конфігураційні константи
src/car_catalog/models.py     модель даних Car
src/car_catalog/services.py   business logic і власний виняток
src/car_catalog/main.py       точка входу: демо і меню
tests/test_services.py        unit tests
```
