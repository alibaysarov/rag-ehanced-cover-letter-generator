# AI Agent Instructions for RAG Enhanced Cover Letter Generator

## Architecture Overview

**Dual-service application**: FastAPI backend (Python 3.10+) + React/TypeScript frontend. Core purpose: RAG-powered cover letter generation using PDF resume extraction, Qdrant vector search, and OpenAI GPT.

**Data flow**: PDF → chunks → embeddings (text-embedding-3-large, 3072-dim) → Qdrant → vector search → GPT letter generation.

**Critical dual-database pattern**: 
- PostgreSQL (port 5433) stores metadata (users, CVs, letters) via SQLModel
- Qdrant (port 6333) stores resume vectors for semantic search
- `source_id` field links both systems (critical for filtering search results by user's CV)

## Project Structure Conventions

### Backend (`backend/`)
- `app/services/` - Business logic (letter generation, PDF processing, embeddings)
- `app/repository/` - Database access layer (async SQLAlchemy operations)
- `app/models/` - SQLModel definitions (table=True for DB tables)
- `app/api/v1/endpoints/` - FastAPI route handlers (use dependency injection for services)
- `app/storage/repository/` - Vector DB operations (Qdrant wrapper)

**Pattern**: Service classes accept `AsyncSession` in constructor for DB operations. Example: `LetterService(session)` → internally creates `CVRepository(session)`.

### Frontend (`frontend/src/`)
- `features/` - Feature-based organization (auth, letter generation)
- `features/{feature}/api/` - API client functions
- `features/{feature}/components/` - Feature-specific React components
- `pages/` - Top-level page components

## Critical Developer Workflows

### Environment Setup
1. **Backend**: `cd backend && uv sync` (uses uv, not pip)
2. **Database**: `make up` starts PostgreSQL + Qdrant containers
3. **Migrations**: `make alembic-upgrade` (uses `scripts/alembic_docker.py` wrapper)
4. **Run backend**: `make dev` (uvicorn with reload on 127.0.0.1:8000)
5. **Frontend**: `cd frontend && npm install && npm run dev` (Vite on port 5173)

**Port mapping quirk**: PostgreSQL container exposes 5433 externally but uses 5432 internally. Check docker-compose.yaml for actual mappings.

### Database Operations
- Create migration: `make alembic-revision msg="description"`
- Apply migrations: `make alembic-upgrade`
- Rollback: `make alembic-downgrade`
- Direct DB shell: `make dbshell`

**Important**: Database connection uses `DATABASE_URL` from .env. Alembic commands route through docker containers via scripts/alembic_docker.py.

## Key Technical Patterns

### Async/Await Everywhere
All database operations, service methods, and API endpoints use async/await. Example from [letter.py](backend/app/api/v1/endpoints/letter.py):
```python
async def create_letter_from_url(
    url: str = Form(...),
    source_id: int = Form(...),
    letter_service: LetterService = Depends(get_letter_service),
    db: AsyncSession = Depends(get_db)
):
```
### Coding rules
never import as backend.app use app.{module_name} only
### RAG Search Pattern
From [letter.py service](backend/app/services/letter.py#L66-L79):
```python
# Embed query → search Qdrant → filter by source_id
query_vec = self.pdf_service.embed_texts([query])[0]
found = self.storage.search(query_vector=query_vec, top_k=10)
filtered_contexts = [c for c, s in zip(found["contexts"], found["sources"]) 
                     if s.get("source_id") == source_id]
```

**Critical**: Always filter Qdrant results by `source_id` to return only the current user's CV chunks.

### PDF Processing Pipeline
See [pdf.py](backend/app/services/pdf.py#L23-L46):
1. Load PDF with llama_index PDFReader
2. Chunk with SentenceSplitter (1000 chars, no overlap)
3. Embed with OpenAI text-embedding-3-large (3072 dimensions)
4. Generate IDs: `abs(hash(f"{filename}_{source_id}_{chunk_index}"))`
5. Upsert to Qdrant with payload containing `user_id`, `source_id`, `text`, `chunk_index`
6. Save CV metadata to PostgreSQL (filename, file_size, source_id)

### Dependency Injection Pattern
Services injected via FastAPI dependencies:
```python
def get_letter_service(db: AsyncSession = Depends(get_db)) -> LetterService:
    return LetterService(db)

# In endpoint
async def endpoint(letter_service: LetterService = Depends(get_letter_service)):
    ...
```

### Configuration Management
Settings in [config.py](backend/app/core/config.py) using environment variables. Key vars:
- `OPENAI_API_KEY` - Required for embeddings and generation
- `DATABASE_URL` - PostgreSQL connection (default uses localhost:5432)
- `QDRANT_URL` - Vector DB (default http://localhost:6333)

## Frontend Architecture

### React Query for State Management
API calls wrapped in TanStack Query hooks. Pattern from features:
```typescript
const { mutate: generateLetter } = useMutation({
  mutationFn: (data) => api.post('/letter/url', data),
  onSuccess: (response) => { /* handle */ }
})
```

### Chakra UI Components
All UI uses Chakra UI. Form validation with react-hook-form + Zod schemas.

### Authentication Flow
JWT-based auth stored in localStorage. [AuthMiddleware](backend/app/middleware/auth.py) checks Bearer token on protected routes. CurrentUser dependency pattern:
```python
CurrentUser = Annotated[User, Depends(get_current_user)]

async def endpoint(current_user: CurrentUser):
    # current_user is authenticated User object
```

## Common Pitfalls

1. **source_id confusion**: Must be consistent between PostgreSQL CVs table and Qdrant payloads
2. **Async session management**: Always pass AsyncSession to repositories, never create new sessions in services
3. **Port conflicts**: PostgreSQL on 5433 (external), Qdrant on 6333, backend on 8000, frontend on 5173
4. **uv vs pip**: Project uses uv for Python dependency management (see pyproject.toml)
5. **Vector dimensions**: Must match text-embedding-3-large (3072). Don't change EMBED_DIM without re-embedding all data

## Testing & Debugging

- Backend logs: Check terminal running `make dev`
- Frontend: Browser console + React Query DevTools
- Database: `make dbshell` for direct psql access
- Qdrant: Web UI at http://localhost:6333/dashboard
- Health check: http://localhost:8000/health

## Integration Points

- **OpenAI API**: Called in [pdf.py](backend/app/services/pdf.py) for embeddings, [letter.py](backend/app/services/letter.py) for generation
- **Qdrant**: Vector search wrapper in [qdrant.py](backend/app/storage/repository/qdrant.py)
- **PostgreSQL**: SQLModel ORM, see [models/](backend/app/models/) for schema
- **CORS**: Configured in [main.py](backend/app/main.py#L48-L54) for localhost:5173 and :3000
