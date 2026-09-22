# RAG Enhanced Cover Letter Generator

AI-powered cover letter generator using Retrieval-Augmented Generation (RAG) and PostgreSQL full-text search.

## Features

- Generate cover letters from a job-posting URL or a job title and description.
- Retrieve relevant project context with PostgreSQL `tsvector` search.
- Choose OpenAI, Anthropic, or a local Ollama model.

## Setup

### Prerequisites

- Docker and Docker Compose
- An LLM provider: OpenAI, Anthropic, or a local Ollama instance

### Start the application

1. Clone the repository:

   ```bash
   git clone git@github.com:alibaysarov/rag-ehanced-cover-letter-generator.git
   cd rag-ehanced-cover-letter-generator
   ```

2. Create the backend environment file and set the required values (database credentials, `SECRET_KEY`, and LLM settings):

   ```bash
   cp backend/.env.example backend/.env
   ```

   For Ollama running on your machine, set `OLLAMA_HOST=http://host.docker.internal:11434` in `backend/.env` and download the selected model before starting the stack:

   ```bash
   ollama pull qwen3:1.7b
   ```

3. Build and start the Docker development stack:

   ```bash
   cd backend
   docker compose -f docker-compose.local.yml up --build -d
   ```

4. Apply database migrations:

   ```bash
   docker compose -f docker-compose.local.yml exec backend uv run alembic upgrade head
   ```

The frontend is available at http://localhost:5173 and the backend at http://localhost:8000.

To stop the stack:

```bash
docker compose -f docker-compose.local.yml down
```
