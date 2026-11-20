FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COHORT_DB_PATH=/data/cohort.db

WORKDIR /app
COPY python/pyproject.toml ./pyproject.toml
COPY python/src ./src
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 cohort && mkdir -p /data && chown -R cohort:cohort /app /data
USER cohort

EXPOSE 8000
CMD ["uvicorn", "cerbere_cohort.api:app", "--host", "0.0.0.0", "--port", "8000"]
