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

alembic-revision:
	@echo "Creating new migration..."
	python scripts/alembic_docker.py revision --autogenerate -m "$(msg)"

alembic-upgrade:
	@echo "Applying migrations..."
	python scripts/alembic_docker.py upgrade head

alembic-current:
	@echo "Current migration status..."
	python scripts/alembic_docker.py current

alembic-history:
	@echo "Migration history..."
	python scripts/alembic_docker.py history

alembic-downgrade:
	@echo "Rolling back last migration..."
	python scripts/alembic_docker.py downgrade -1

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