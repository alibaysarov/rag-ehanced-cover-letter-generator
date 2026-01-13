# RAG Enhanced Cover Letter Generator

AI-powered cover letter generator using Retrieval-Augmented Generation (RAG) with vector search.

## Features

- **Resume Upload**: Upload PDF resumes to vector database
- **URL-based Generation**: Generate cover letters from job posting URLs
- **Text-based Generation**: Generate cover letters from job title and description
- **RAG Technology**: Uses vector search to find relevant resume content
- **PostgreSQL/SQLite**: Flexible database support

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL/SQLite
- **AI**: OpenAI GPT-4, Vector Embeddings
- **Vector DB**: Qdrant
- **Frontend**: React, TypeScript, Chakra UI

## Setup

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for PostgreSQL)
- OpenAI API Key

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
   cp env.example .env

   # Edit .env with your settings
   nano .env
   ```

3. **Database Setup**

   Start PostgreSQL and Qdrant:
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
| POST | `/upload-cv` | Upload resume PDF to vector database |
| POST | `/url` | Generate cover letter from job posting URL |
| POST | `/text` | Generate cover letter from job title/description |

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Database (PostgreSQL)
POSTGRES_USER=cover_letter_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=cover_letter_db
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# PostgreSQL settings are configured via Docker environment

# Qdrant
QDRANT_URL=http://localhost:6333

# App Settings
APP_ENV=development
DEBUG=True
```

## Database Schema

### Tables
- **users**: User accounts with email and password
- **cvs**: Resume metadata (belongs to users)
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

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres
docker-compose up -d qdrant

# View logs
docker-compose logs -f
```

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
│   └── storage/             # Vector storage
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
- [ ] Set secure `OPENAI_API_KEY`
- [ ] Configure Qdrant for production
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
