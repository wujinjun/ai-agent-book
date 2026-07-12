FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY projects/10-enterprise-platform/main.py ./main.py
COPY projects/10-enterprise-platform/api.py ./api.py
RUN pip install --no-cache-dir pydantic==2.11.7 fastapi==0.116.1 uvicorn==0.35.0 \
    SQLAlchemy==2.0.51 'psycopg[binary]==3.3.4' redis==8.0.1
RUN mkdir -p /app/data && chown -R 65532:65532 /app/data
ENV PYTHONPATH=/app/src APP_MODE=offline DATABASE_PATH=/app/data/platform.db
USER 65532:65532
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
