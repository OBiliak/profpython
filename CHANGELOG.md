# Changelog

Версії за semantic versioning (MAJOR.MINOR.PATCH): 0.N.0 — лабораторна робота №N, 1.0.0 — перший
production-ready release.

## [1.0.0] — 2026-11-08 (лабораторна робота №10)
### Added
- Налаштування з environment variables і `.env` (pydantic-settings): APP_NAME, ENVIRONMENT, DATABASE_URL,
  LOG_LEVEL, HOST, PORT, SEED_DEMO_DATA; `.env.example` без секретів.
- GET /health — стан сервісу і БД (200 або 503).
- Production entry point `car-catalog` (main.py): logging, міграції Alembic, демо-дані, Uvicorn.
- Packaging: metadata, LICENSE (MIT), wheel і sdist; міграції всередині пакета.
- Dockerfile (multi-stage, non-root user, HEALTHCHECK, volume для SQLite) і .dockerignore.
- GitHub Actions: ruff check, ruff format --check, mypy, pytest з coverage (Python 3.11 і 3.12), build з artifact,
  docker build зі smoke test.
- Ruff (lint і format), експорт OpenAPI у docs/openapi.json, README для production.
### Changed
- Демонстрацію ЛР9 перенесено з main.py у performance_demo.py.
- DATABASE_URL замість CAR_CATALOG_DATABASE_URL; `alembic` бере URL з налаштувань.

## [0.9.0] — лабораторна робота №9
Профілювання (cProfile, tracemalloc, timeit), ThreadPoolExecutor, ProcessPoolExecutor, NumPy, lru_cache, benchmarks.

## [0.8.0] — лабораторна робота №8
REST API на FastAPI, Pydantic schemas, асинхронний клієнт HTTPX (Task, gather, Semaphore, retry, timeout).

## [0.7.0] — лабораторна робота №7
SQLite, SQLAlchemy ORM, Repository, транзакції, міграції Alembic.

## [0.6.0] — лабораторна робота №6
Test suite на pytest: fixtures, parametrize, mocks, coverage.

## [0.5.0] — лабораторна робота №5
Імпорт і експорт CSV / JSON / YAML, власні винятки, logging, атомарний запис.

## [0.4.0] — лабораторна робота №4
ООП-модель каталогу, протоколи, dataclasses, mypy.

## [0.3.0] — лабораторна робота №3
Ітератори, генератори, потокова обробка.

## [0.2.0] — лабораторна робота №2
Структури даних, функції аналізу, декоратори, benchmark пошуку.

## [0.1.0] — лабораторна робота №1
Структура проєкту, модель Car, консольний застосунок.
