FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY projects/08-research-workflow/main.py ./main.py
RUN pip install --no-cache-dir pydantic==2.11.7 langgraph==1.2.9
ENV PYTHONPATH=/app/src APP_MODE=offline
USER 65532:65532
CMD ["python", "main.py"]
