---
description: "Scaffold a new REST API endpoint in apps/server: router, validation middleware, service function, and shared Zod schema. Provide the HTTP method, resource name, and optionally a request/response shape."
argument-hint: "e.g. POST /conversations — create a new conversation"
agent: "agent"
tools: [search, editFiles, problems]
model: Claude Opus 4.6 (copilot)
---

Follow the [backend instructions](../instructions/backend.instructions.md) and [AI integration instructions](../instructions/ai-integration.instructions.md) throughout.

## Task

Scaffold a complete, production-ready endpoint for the following:

**$input** <!-- e.g. "POST /api/v1/letter — create a new cover letter" -->

---

## Steps to complete

### 1. Pydantic schema (`backend/app/schemas/`)

- Create or update the relevant schema file (e.g. `letter.py`).
- Define request and response models extending `BaseModel` or `GeneralResponse`.
- Include `success: bool`, `data`, `message`, `errors` fields per project convention.

### 2. SQLModel (if new table) (`backend/app/models/`)

- Create model class with `table=True` inheriting from `SQLModel`.
- Add `id`, `created_at`, `updated_at` fields.
- Define foreign keys with `Field(foreign_key="table.column", index=True)`.
- Add bidirectional relationships with `back_populates`.
- Create Alembic migration: `make alembic-revision msg="create_<table>_table"`.

### 3. Repository (`backend/app/repository/<resource>_repository.py`)

- Constructor accepts `AsyncSession`.
- Implement `create_*`, `get_*_by_*`, `get_*_list`, `delete_*` async methods.
- Use SQLAlchemy `select()` for queries.
- Commit + refresh pattern after writes.

### 4. Service (`backend/app/services/<resource>.py`)

- Accept `AsyncSession` or repositories in `__init__`.
- Orchestrate business logic, raise `HTTPException` on errors.
- Wrap external API calls in try/except.

### 5. Endpoint (`backend/app/api/v1/endpoints/<resource>.py`)

- Create FastAPI `APIRouter` with tag and prefix.
- Use `Depends()` for service and `CurrentUser` injection.
- All handlers must be `async def`.
- Register router in `backend/app/api/v1/api.py`.

### 6. Dependency function (`backend/app/api/v1/endpoints/<resource>.py`)

- Add `get_<resource>_service(db: AsyncSession = Depends(get_db))` factory.

### 7. Verify

- Run the dev server: `make dev`.
- Check for import errors and test the endpoint.

---

## Constraints

- Always import as `from app.{module}` — never `from backend.app`.
- All handlers must be `async def`.
- Services receive `AsyncSession` via dependency injection — never create sessions internally.
- Use `HTTPException` with specific status codes for errors.
- Always include `success: bool` in response models.
- `source_id` must stay consistent between PostgreSQL and Qdrant.
- Do not expose internal error details to the client.
