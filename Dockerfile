# Stage 1: build
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Stage 2: runtime
FROM python:3.11-slim
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
USER app
EXPOSE 8000
CMD ["uvicorn", "dnscope.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

