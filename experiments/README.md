# Експерименти лабораторної роботи №6

Навмисно слабкі та flaky tests — НЕ входять в основний test suite (testpaths = tests).
Запуск з кореня проєкту, наприклад: `python -m pytest experiments/test_exp1_weak_vs_strong.py -v`.

| Файл | Експеримент |
|---|---|
| test_exp1_weak_vs_strong.py, buggy_average.py | 1 weak vs strong tests; 2 coverage без assertions |
| test_exp3_branch.py, price_segments.py | 3 branch coverage |
| test_exp4_mock_vs_fake.py | 4 Mock vs fake |
| test_exp5_flaky.py, car_of_day.py | 5 flaky test і deterministic версія |
| test_exp6_tmp_path.py | 6 tmp_path isolation |
| tests/unit/test_vehicle_info.py | 7 failure path (success / failure, assert_not_called) |
