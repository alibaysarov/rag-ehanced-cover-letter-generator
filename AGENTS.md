# Repository Guidelines

## Project Structure & Module Organization

This is a RAG-powered cover-letter application with a FastAPI backend and Vite/React frontend. Backend code lives in `backend/app/`: API routes are in `api/v1/endpoints/`, business logic in `services/`, persistence models in `models/`, repositories in `repository/`, and request/response schemas in `schemas/`. Database migrations are under `backend/alembic/versions/`; backend tests are in `backend/tests/`.

Frontend code is in `frontend/src/`. Keep route-level screens in `pages/`, shared UI in `components/`, feature-specific code in `features/<feature>/`, reusable hooks in `hooks/`, and translations in `i18n/locales/`. Product and implementation notes belong in `specs/`.

## Build, Test, and Development Commands

Run commands from the component directory unless noted otherwise.

- `cd backend && uv sync` installs Python dependencies.
- `cd backend && make up` starts local Docker services; `make migrate` applies Alembic migrations.
- `cd backend && make dev` runs FastAPI with reload at `127.0.0.1:8000`.
- `cd backend && make lint` runs Pyright; `make pre-commit-fix` sorts imports, removes unused imports, and formats Python.
- `cd backend && uv run python -m unittest discover -s tests` runs the backend test suite.
- `cd frontend && npm install && npm run dev` starts Vite; `npm run build` type-checks and creates a production build.

## Coding Style & Naming Conventions

Use four-space indentation for Python and follow Ruff formatting/import ordering. Use `snake_case` for Python modules, functions, and variables; `PascalCase` for classes and Pydantic/SQLAlchemy models. Keep migrations named descriptively, for example `add_generation_time_ms_to_sent_letters.py`.

Use TypeScript for frontend changes. React components and pages use `PascalCase` filenames (for example, `LetterGenerator.tsx`); hooks begin with `use` (for example, `useLetter.ts`). Follow `frontend/.prettierrc` when formatting UI code.

## Testing Guidelines

Add focused tests beside the backend test suite using `test_<behavior>.py`, and name async test methods `test_<action>_<expected_result>`. Prefer lightweight fakes for repository/service unit tests, as in `tests/test_auto_parse_job_repository.py`. Run the affected tests and `make lint` before requesting review. The frontend has Vitest dependencies but no configured test script; add one when introducing frontend tests.

## Commit & Pull Request Guidelines

Recent history favors short, imperative summaries such as `added redis listeners`, `fixed websocket handler`, and `linting fixes`. Write one focused change per commit; use a concise present-tense subject and avoid unrelated formatting churn. Pull requests should explain the user-visible or architectural change, note migrations/configuration changes, link the relevant issue when available, and include screenshots for frontend changes. Never commit `.env`, API keys, or generated runtime files.
