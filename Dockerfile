FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Instala dependências essenciais do sistema para compilar pacotes se necessário
RUN apt-get update && apt-get install -y git libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-cache

COPY . .
RUN chmod +x /app/start.sh

RUN useradd --create-home appuser && chown -R appuser:appuser /app /opt/venv
USER appuser

EXPOSE 8000

ENTRYPOINT ["sh", "/app/start.sh"]
