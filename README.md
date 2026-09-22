# RAG Enhanced Cover Letter Generator

AI-powered cover letter generator using Retrieval-Augmented Generation (RAG) with PostgreSQL full-text search.

## Features

- **Resume Upload**: Upload PDF resumes and store searchable chunks in PostgreSQL
- **URL-based Generation**: Generate cover letters from job posting URLs
- **Text-based Generation**: Generate cover letters from job title and description
- **RAG Technology**: Uses PostgreSQL `tsvector` search and project data to find relevant resume context
- **PostgreSQL/SQLite**: Flexible database support

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL/SQLite
- **AI**: LangChain with OpenAI, Anthropic, or Ollama
- **Search**: PostgreSQL full-text search
- **Frontend**: React, TypeScript, Chakra UI

## Setup

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for PostgreSQL)
- An LLM provider: OpenAI, Anthropic, or local Ollama

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag-enhanced-cover-letter-generator
   ```

2. **Backend Setup**

   ```bash
   cd backend

   # Install dependencies
   uv sync

   # Copy environment file
   cp .env.example .env

   # Edit .env with your settings
   nano .env
   ```

3. **Database Setup**

   Start PostgreSQL:
   ```bash
   cd backend
   make up
   ```
   
   Run migrations:
   ```bash
   cd backend
   source .venv/Scripts/activate (для Windows) source .venv/bin/activate (для macos)
   make  migrate
   ```

4. **Frontend Setup**

   ```bash
   cd frontend

   # Install dependencies
   npm install
   ```

## Running the Application

### Start Backend

```bash
cd backend
make dev
```

This will start the FastAPI server on http://127.0.0.1:8000

### Start Frontend

```bash
cd frontend
npm run dev
```

This will start the React development server on http://localhost:5173

## API Endpoints

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register a new user |
| POST | `/login` | Login and get JWT tokens |
| POST | `/refresh` | Refresh access token using refresh token |
| GET | `/me` | Get current user information (requires auth) |
| POST | `/logout` | Logout user |

### CV Management (`/api/v1/cv`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/{cv_id}` | Update CV by ID (upload new PDF) |
| DELETE | `/{cv_id}` | Delete CV by ID |

### User CVs (`/api/v1/user`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/cvs` | Get all CVs for current user |
| GET | `/cvs/options` | Get CV options (id/name pairs) for dropdowns |

### Letter Generation (`/api/v1/letter`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-cv` | Upload resume PDF to PostgreSQL-backed RAG storage |
| POST | `/url` | Generate cover letter from job posting URL |
| POST | `/text` | Generate cover letter from job title/description |

## Configuration

### Environment Variables

```bash
# LLM (only these three values select the chat model)
LLM_PROVIDER=ollama
LLM_API_KEY=
LLM_MODEL=qwen3:1.7b

# Only needed when LLM_PROVIDER=ollama.
# With `make dev` use localhost; with Docker Compose use host.docker.internal.
OLLAMA_HOST=http://localhost:11434

# Database (PostgreSQL)
POSTGRES_USER=cover_letter_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=cover_letter_db
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# App Settings
APP_ENV=development
DEBUG=True
```

### Connecting an LLM

Set the LLM variables in `backend/.env`. The application creates the corresponding
LangChain chat model automatically, so application code does not need provider-specific
configuration.

| Provider | `LLM_PROVIDER` | `LLM_API_KEY` | Example `LLM_MODEL` |
|----------|----------------|---------------|---------------------|
| OpenAI | `openai` | Your OpenAI API key | `gpt-4.1-mini` |
| Anthropic | `anthropic` | Your Anthropic API key | `claude-sonnet-4-20250514` |
| Ollama | `ollama` | Leave empty | `qwen3:1.7b` |

For example, to use Anthropic:

```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=your_anthropic_api_key
LLM_MODEL=claude-sonnet-4-20250514
```

For local Ollama, install and start Ollama, then download the chosen model before
starting the backend:

```bash
ollama pull qwen3:1.7b
```

When the backend is launched with `make dev`, use `OLLAMA_HOST=http://localhost:11434`.
When it runs in Docker Compose, use `OLLAMA_HOST=http://host.docker.internal:11434`.
OpenAI and Anthropic do not require `OLLAMA_HOST`.

## Database Schema

### Tables
- **users**: User accounts with email and password
- **cvs**: Resume metadata (belongs to users)
- **cv_chunks**: Searchable resume chunks for RAG context
- **projects**: Structured project data parsed from CVs
- **letters**: Generated cover letters (belongs to CVs)

### Relationships
- User (1) → (many) CV
- CV (1) → (many) Letter

### Database Setup & Migrations

#### Quick Setup
```bash
# Start database and apply migrations
make setup
```

#### Manual Setup Steps

1. **Start PostgreSQL container**
   ```bash
   make up
   # or
   docker-compose up -d postgres
   ```

2. **Apply migrations**
   ```bash
   make alembic-upgrade
   ```

#### Working with Alembic Migrations

All Alembic commands are wrapped to work with Docker environment:

```bash
# Apply all pending migrations
make alembic-upgrade

# Check current migration status
make alembic-current

# View migration history
make alembic-history

# Rollback last migration
make alembic-downgrade
```

#### Creating New Migrations

To create a new migration when you modify models:

1. **Make changes to your models** in `backend/app/models/`
2. **Create migration file** by copying and modifying existing migration in `alembic/versions/`
3. **Update upgrade() and downgrade()** functions with proper SQL
4. **Apply migration**: `make alembic-upgrade`

Example migration structure:
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('new_field', sa.String(100)))

def downgrade() -> None:
    op.drop_column('users', 'new_field')
```

#### Migration Architecture

- **alembic/versions/**: Contains migration files with upgrade/downgrade logic
- **scripts/alembic_docker.py**: Docker-aware wrapper for Alembic commands
- **backend/alembic.ini**: Alembic configuration
- **backend/alembic/env.py**: Migration environment setup

For Windows/Docker environment, migrations are applied through Docker containers to ensure compatibility.

## Docker Services

Run Docker Compose commands from `backend/`.

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres

# View logs
docker-compose logs -f
```

The local stack uses one image, `cover-letter-backend:local`, for `backend`,
`celery-worker`, and `celery-beat`. Only the `backend` service builds it; the Celery
services reuse it with their own commands. Build the shared image before starting
Celery on its own:

```bash
cd backend
make build-backend
docker compose -f docker-compose.local.yml up -d --renew-anon-volumes backend celery-worker celery-beat

# Rebuild once and update all three services after dependency/image changes.
make restart-backend
```

Existing containers keep using their previous image until recreated. Old images
are not deleted automatically. `--renew-anon-volumes` refreshes each service's
`/app/.venv` from the shared image; named database volumes are preserved. The
standard `docker-compose.yaml` uses the same image name for its backend service.

## Development

### Code Structure
```
backend/
├── app/
│   ├── api/v1/endpoints/     # API endpoints
│   ├── core/                 # Configuration
│   ├── models/              # SQLAlchemy models
│   ├── repository/          # Data access layer
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
├── alembic/                 # Database migrations
└── tests/                   # Unit tests

frontend/
├── src/
│   ├── components/          # React components
│   ├── pages/              # Page components
│   ├── hooks/              # Custom hooks
│   └── types/              # TypeScript types
```

### Testing

```bash
# Run backend tests
cd backend && python -m pytest

# Run frontend tests
cd frontend && npm test
```

## Deployment

### Production Checklist
- [ ] Set `USE_SQLITE=false`
- [ ] Configure PostgreSQL in production
- [ ] Set `LLM_PROVIDER`, `LLM_API_KEY` (if required), and `LLM_MODEL`
- [ ] Set `APP_ENV=production`
- [ ] Enable HTTPS
- [ ] Configure proper CORS origins

### Docker Production

```bash
# Build and run
docker-compose -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit pull request

## License

MIT License
# Parallel auto-parse

The local stack uses one Celery worker with four prefork slots. Run migrations from the API container with `uv run alembic upgrade head`, then start the local services. `POST /auto-parse/start` returns immediately and workers parse the registered sites in parallel; progress is SSE and saved vacancies arrive over WebSocket.

The implementation does not recover jobs after a worker SIGKILL/OOM, unavailable database during error persistence, or a process crash between a database commit and Redis publish. Reload/reconnect restores results through the vacancies API. Run backend checks with `uv run python -m unittest discover -s tests` and frontend checks with `npm run test && npm run build`.
