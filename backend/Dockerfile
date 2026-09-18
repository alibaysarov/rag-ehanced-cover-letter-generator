FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

FROM base AS builder

# Install dependencies in a cacheable layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --python /usr/local/bin/python3.12

# Install the application into the already-created virtual environment.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --python /usr/local/bin/python3.12

FROM base AS runtime

# Copy only application files and the completed environment; build cache and
# intermediate virtual-environment layers are not part of the final image.
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# The application launches Chromium only in headless mode, so install the
# headless shell rather than both the full browser and the shell.
RUN playwright install --with-deps --only-shell chromium

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
