# Two stages: the first builds the wheel, the second contains only Python and the installed wheel.

# --- stage 1: build the package ---
FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m pip install --no-cache-dir build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m build --wheel

# --- stage 2: production image ---
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_URL=sqlite:////app/data/car_catalog.db
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN python -m pip install --no-cache-dir /tmp/*.whl \
    && rm /tmp/*.whl \
    && useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown appuser /app/data
# the service does not run as root
USER appuser
# SQLite database file is kept outside the container: docker run -v car_catalog_data:/app/data
VOLUME ["/app/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT}/health', timeout=2)"
# car-catalog = car_catalog.main:main: migrations, optional demo data, Uvicorn
CMD ["car-catalog"]
