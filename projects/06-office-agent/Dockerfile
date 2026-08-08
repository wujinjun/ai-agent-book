FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE-CODE ./
COPY src ./src
COPY projects/06-office-agent/main.py ./main.py
RUN pip install --no-cache-dir pydantic==2.11.7 httpx==0.28.1
ENV PYTHONPATH=/app/src APP_MODE=offline AUDIT_PATH=/tmp/office-audit.jsonl
USER 65532:65532
CMD ["python", "main.py"]
