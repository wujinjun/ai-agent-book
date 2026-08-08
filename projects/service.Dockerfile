FROM python:3.12-slim AS runtime

ARG PROJECT_SLUG
WORKDIR /app
COPY pyproject.toml README.md LICENSE-CODE ./
COPY src ./src
COPY projects/${PROJECT_SLUG}/api.py ./api.py
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data && chown -R 65532:65532 /app/data

ENV PYTHONPATH=/app/src \
    APP_MODE=offline \
    DATABASE_PATH=/app/data/project.db \
    PYTHONUNBUFFERED=1
USER 65532:65532
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
