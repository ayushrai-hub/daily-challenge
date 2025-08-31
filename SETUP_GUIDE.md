# Daily Challenge Application Setup Guide

## Database Configuration

The Daily Challenge application uses PostgreSQL for data storage. The database is configured with the following details:

- **Database Name**: dcq_db
- **Username**: dcq_user
- **Password**: dcq_pass
- **Port**: 5433 (non-standard to avoid conflicts)
- **Connection URL**: `postgresql://dcq_user:dcq_pass@localhost:5433/dcq_db`

## Docker Setup

The PostgreSQL database is running in a Docker container for development. Key features:

- Uses the official PostgreSQL 15 image
- Persistent volume for data retention across container restarts
- Can be managed using the provided `docker-compose.yml` file

## Database Initialization

The database schema and test data can be initialized using the provided script:

```bash
./scripts/init_db.sh
```

This script:
1. Drops existing tables and PostgreSQL enum types to ensure a clean slate
2. Runs all Alembic migrations to create the proper schema
3. Creates test data for users, problems, and content sources

## API Server

The API server is built with FastAPI and can be started with:

```bash
uvicorn app.main:app --reload --port 8000
```

## Test Users

The following test users are created during database initialization:

| ID | Email                | Password        | Active | Admin |
|----|----------------------|-----------------|--------|-------|
| 1  | admin@example.com    | testpassword123 | Yes    | Yes   |
| 2  | user@example.com     | testpassword123 | Yes    | No    |
| 3  | inactive@example.com | testpassword123 | No     | No    |
| 4  | recent@example.com   | testpassword123 | Yes    | No    |
| 5  | admin2@example.com   | testpassword123 | Yes    | Yes   |

## Test Problems

The initialization also creates test problems with different attributes:

| ID | Title                                      | Difficulty | Status   |
|----|-------------------------------------------|------------|----------|
| 1  | Test Problem 1: Easy String Manipulation  | easy       | approved |
| 2  | Test Problem 2: Medium Array Challenge    | medium     | approved |
| 3  | Test Problem 3: Hard Dynamic Programming  | hard       | archived |
| 4  | Test Problem 4: Recent Medium Problem     | medium     | draft    |
| 5  | Test Problem 5: Easy Array Problem        | easy       | approved |

## Test Content Sources

The following content sources are created for testing:

| ID | Platform       | Title                                     | Status    |
|----|---------------|------------------------------------------|-----------|
| 1  | stackoverflow | Test StackOverflow Question 1            | processed |
| 2  | gh_issues     | Test GitHub Issue 789                    | pending   |
| 3  | blog          | Test Blog Article on Algorithm Complexity | failed    |
| 4  | reddit        | Test Reddit Post on Backend Development  | processed |
| 5  | hackernews    | Test HN Post on AI Algorithms            | pending   |

## API Filtering

The API supports various filtering options for each endpoint:

- Users: filter by email, active status, admin status, and creation date
- Problems: filter by title, difficulty, status, and creation date
- Content Sources: filter by title, platform, processing status, and relevant dates

## Testing API Filtering

Use the provided test scripts to verify filtering functionality:

```bash
python scripts/test_problems_filtering.py
python scripts/test_content_sources_filtering.py
```

## Notes on Database Persistence

- The database uses a Docker volume to maintain data between container restarts
- To completely reset the database, you can remove the volume with `docker-compose down -v`
- Run `init_db.sh` after database reset to recreate the schema and test data

## Authentication

The application uses OAuth2 with JWT tokens for authentication:
- Login endpoint: `POST /api/auth/login`
- Get current user: `GET /api/auth/me`
- Register new user: `POST /api/auth/register`
