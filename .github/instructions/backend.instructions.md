---
applyTo: "backend/**"
description: "Use when: writing or modifying Python backend code — FastAPI endpoints, services, repositories, models, schemas, middleware, database operations, or configuration."
---

# Backend Instructions — FastAPI + SQLModel + Async

## Stack

- **Framework**: FastAPI (≥0.128) with Uvicorn ASGI server
- **ORM**: SQLModel (SQLAlchemy + Pydantic hybrid) with async sessions
- **Database**: PostgreSQL (port 5433 external / 5432 internal) via `psycopg2-binary`
- **Migrations**: Alembic (through `scripts/alembic_docker.py` wrapper)
- **Auth**: JWT (PyJWT + HS256), password hashing via passlib (pbkdf2_sha256)
- **Package manager**: `uv` (never pip)
- **Python**: 3.10+

## Project Structure

```
backend/app/
├── api/v1/endpoints/   # Route handlers (thin — delegate to services)
├── core/config.py      # Settings singleton from env vars
├── database.py         # Engine + session factory
├── helper/             # Small utilities (e.g. user lookup helper)
├── middleware/auth.py   # AuthMiddleware (BaseHTTPMiddleware)
├── models/             # SQLModel table definitions (table=True)
├── repository/         # Data access layer (async DB operations)
├── schemas/            # Pydantic request/response models
├── services/           # Business logic (orchestrates repos + external APIs)
└── storage/repository/ # Vector DB wrapper (Qdrant)
```

## Import Rules

- **Always** `from app.{module}` — never `from backend.app`
- Standard lib → third-party → local app imports
- Type hints: `from typing import Optional, List, Annotated`

## Async/Await

All database operations, service methods, and endpoint handlers **must** be async:

```python
async def create_item(
    item_service: ItemService = Depends(get_item_service),
    db: AsyncSession = Depends(get_db),
):
    result = await item_service.do_thing()
    return result
```

## Dependency Injection

Chain: `get_db` → `get_{repository}` → `get_{service}` → endpoint parameter.

```python
def get_cv_repository(session: AsyncSession = Depends(get_db)) -> CVRepository:
    return CVRepository(session)

def get_letter_service(db: AsyncSession = Depends(get_db)) -> LetterService:
    return LetterService(db)
```

**CurrentUser pattern** for protected endpoints:

```python
CurrentUser = Annotated[User, Depends(get_current_user)]

async def endpoint(current_user: CurrentUser):
    ...
```

## Models (SQLModel)

- Inherit from `SQLModel` with `table=True`
- Primary keys: `Optional[int] = Field(default=None, primary_key=True)`
- Foreign keys: `Field(foreign_key="table.column", index=True)`
- Relationships: bidirectional with `back_populates`, use `cascade="all, delete-orphan"` for owned children
- Timestamps: `created_at`, `updated_at` as `datetime` fields
- Table naming: plural lowercase (`users`, `cvs`, `letters`)

## Repository Layer

- Constructor accepts `AsyncSession` (or `Session` for UserRepository)
- Methods: `create_*`, `get_*_by_*`, `get_*_list`, `update_*`, `delete_*`
- Use `select()` from SQLAlchemy for queries
- Commit + refresh pattern: `session.add(obj)` → `session.commit()` → `session.refresh(obj)`
- Never create sessions inside repositories — always receive via DI

## Service Layer

- Accepts `AsyncSession` or typed repositories in `__init__`
- Orchestrates business logic across repositories and external APIs
- Raises `HTTPException` with appropriate status codes on errors
- Wraps external API calls in try/except

## API Response Pattern

```python
class GeneralResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    errors: Optional[list[str]] = None
```

Extend with `message` or `source_id` fields as needed. Always include `success` boolean.

## Error Handling

- `HTTPException` for client-facing errors with specific `status_code` and `detail`
- `logging.error("...", exc_info=True)` for server errors
- Database rollbacks on failure: `await session.rollback()`
- Never expose internal error details to clients

## Authentication

- Bypass paths: `/health`, `/docs`, `/openapi.json`, `/auth/register`, `/auth/login`
- AuthMiddleware extracts Bearer token → decodes JWT → sets `request.state.user_email`
- `get_current_user()` resolves email → User object, checks `is_active`
- Access tokens: 24h expiry. Refresh tokens: 7 days.

## File Uploads

- Use `Form()` and `File()` from FastAPI
- Validate file size (max 10MB) and extension (.pdf) before processing
- Content type: `multipart/form-data`

## Database Commands

| Action | Command |
|--------|---------|
| Start containers | `make up` |
| Run migrations | `make alembic-upgrade` |
| Create migration | `make alembic-revision msg="description"` |
| Rollback | `make alembic-downgrade` |
| DB shell | `make dbshell` |
| Dev server | `make dev` |

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Routes | lowercase, plural nouns | `/letter`, `/cv`, `/user` |
| Repositories | `{Model}Repository` | `CVRepository` |
| Services | `{Domain}Service` | `LetterService`, `PdfService` |
| Dependencies | `get_{name}` | `get_letter_service` |
| Private methods | `_` prefix | `_parse_job_requirements()` |
| Models | PascalCase singular | `User`, `CV`, `Letter` |
| DB fields | snake_case | `user_id`, `created_at` |

## Critical Rules

1. **source_id** must be consistent between PostgreSQL CVs table and Qdrant payloads
2. **Never create new sessions** inside services — always receive from DI
3. **Port awareness**: PostgreSQL 5433 (external), Qdrant 6333, backend 8000
4. **uv sync** for dependency management, never pip install
5. **Vector dimensions** = 3072 (text-embedding-3-large). Changing EMBED_DIM requires re-embedding all data
