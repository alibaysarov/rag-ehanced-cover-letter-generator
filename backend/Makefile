# Development
dev:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Database operations

# Alembic commands (when database is accessible)

migrate:
	alembic upgrade head

alembic-init:
	@echo "Initializing Alembic..."
	uv run alembic init alembic


lint:
	uv run pyright app/

sort-imports:
	ruff check --select I --fix .

ruff-remove-imports:
	ruff check --select F401 --fix .

# Database shell
dbshell:
	docker-compose exec postgres psql -U cover_letter_user -d cover_letter_db

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Full setup
setup: up alembic-upgrade
	@echo "Database setup complete!" --reload


restart-backend:
	docker compose -f docker-compose.local.yml up --build backend -d

ngrok-start:
	ngrok http --url=https://limpidly-unensnared-anika.ngrok-free.dev 5173