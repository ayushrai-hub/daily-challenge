# Technical Context

**Technologies:**

- Python 3.10+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic V2
- Docker, Docker Compose for local development
- Redis for rate limiting and caching
- Tag management uses a JSONB problem_metadata field to store pending/suggested tags, ensuring no unique constraint violations or session binding issues. Only admin-approved tags are created in the main tag table. TagRepository and ProblemRepository updated for session-safe, case-insensitive lookups. Admin workflow for tag approval is planned.
- **Authentication System:**
  - Using JWT-based authentication with secure token generation and validation
  - Password hashing with bcrypt and proper salt rounds
  - Pydantic schema validation for user input
  - Role-based access control with admin and regular users
  - Authentication middleware to protect routes
  - Rate limiting for sensitive operations such as login
  - Email verification with secure tokens:
    - Cryptographically secure random tokens via `secrets.token_urlsafe()`
    - Time-limited verification (24-hour expiration)
    - Database tracking of token usage states
    - Self-service verification request mechanism
    - Token validation with protection against expired/used tokens
  - Proper token lifetime management
  - Admin vs regular user role separation
- Celery with Redis for background task processing
- Flower for Celery monitoring
- Anthropic Claude for AI-driven task management
- Perplexity API (optional) for research-backed subtasks
- React frontend now uses robust optimistic UI for subscription and tag management.
- Backend serialization pattern for all models with relationships.
- Pydantic schemas are the single source of truth for API response structure.
- Centralized UUID serialization system through custom type annotations.
- SQLAlchemy 2.0 compatible query patterns throughout the codebase.

**Development Setup:**

- `.env` for API keys, DB URLs, and Redis configuration
- Docker Compose file for PostgreSQL
- Docker container for Redis (dcq-redis)
- `requirements.txt` for Python dependencies
- `task-master` CLI for task workflows
- Separate test database (port 5434) and dev database (port 5433)
- `update_without_reset.sh` for non-destructive database updates
- `update_test_db.sh` for test database schema management

**Database Schema Management:**

- PostgreSQL database with proper enum types for all models
- Alembic migrations for database schema version control
- Centralized association tables in association_tables.py to avoid circular dependencies
- Migration files organized by version number and purpose (e.g., 06a_enhance_tag_model.py)
- Fixed enum definitions in all models: TagType, DifficultyLevel, ProblemStatus, ProcessingStatus, etc.
- Enhanced Tag model with comprehensive type system:
  - TagType enum with multiple categories: language, skill_level, topic, framework, tool, domain, concept
  - Self-referential relationship using parent_tag_id for hierarchy
  - Child tags accessible via .children relationship property
  - Parent tag accessible via .parent_tag relationship property
  - API endpoints updated to support tag type filtering and parent-child manipulation
  - Proper validation for tag relationships to prevent circular references
- Many-to-many relationships implemented with proper association tables
- Non-destructive database update process to preserve data
- Development database seeding scripts for creating common tags with proper relationships

**Redis Configuration:**

- Redis is used for rate limiting, caching, and Celery broker/backend
- Redis container: `dcq-redis` running on port 6379
- Connection settings configured in .env file:
  - REDIS_HOST=localhost
  - REDIS_PORT=6379
  - REDIS_DB=0
  - REDIS_PASSWORD=
  - REDIS_URL=redis://localhost:6379/0
- Fallback to in-memory storage if Redis is unavailable for rate limiting

**Rate Limiting:**

- Using slowapi library for rate limiting implementation
- Redis backend for distributed rate limiting
- Configurable limits defined in .env:
  - RATE_LIMIT_DEFAULT=100/minute
  - RATE_LIMIT_REGISTER=5/minute
  - RATE_LIMIT_LOGIN=10/minute

**Celery Configuration:**

- Celery used for background task processing (daily challenge delivery, email sending, content processing)
- Redis used as both message broker and result backend
- Configured task queues:
  - default: General purpose tasks
  - emails: Email delivery tasks
  - content: Content processing and generation tasks
- Periodic task scheduling via Celery Beat:
  - Daily challenge delivery (8:00 AM UTC)
  - Weekly content generation (Monday, 2:00 AM UTC)
  - System health checks (Daily, 0:00 AM UTC)
  - Process pending emails (Every minute for testing)
- Flower dashboard for monitoring (http://localhost:5555)
- Custom base task class with enhanced logging
- Task failure handling with retry mechanisms
