# Makefile for Daily Challenge project
# Provides common commands for database management and development tasks

.PHONY: db-up db-down db-reset db-init db-logs api-run test

# Start the database container
db-up:
	@echo "Starting PostgreSQL database container..."
	docker-compose up -d postgres
	@echo "Database is running on port 5433"

# Stop the database container
db-down:
	@echo "Stopping PostgreSQL database container..."
	docker-compose down

# Reset the database (keeps volume)
db-reset:
	@echo "Resetting the database (keeps volume)..."
	docker-compose down
	docker-compose up -d postgres
	@echo "Database reset complete. Run 'make db-init' to reinitialize the schema and test data."

# Initialize database schema and test data
db-init:
	@echo "Initializing database schema and test data..."
	./scripts/init_db.sh

# View database logs
db-logs:
	docker-compose logs -f postgres

# Run the API server
api-run:
	@echo "Starting the API server..."
	uvicorn app.main:app --reload --port 8000

# Run tests
test:
	@echo "Running tests..."
	python -m pytest

# Complete setup (database + schema + test data)
setup: db-up db-init
	@echo "Setup complete! Database is running with schema and test data."

# Help command
help:
	@echo "Available commands:"
	@echo "  make db-up        - Start the database container"
	@echo "  make db-down      - Stop the database container"
	@echo "  make db-reset     - Reset the database (keeps volume)"
	@echo "  make db-init      - Initialize database schema and test data"
	@echo "  make db-logs      - View database logs"
	@echo "  make api-run      - Run the API server"
	@echo "  make test         - Run tests"
	@echo "  make setup        - Complete setup (database + schema + test data)"
