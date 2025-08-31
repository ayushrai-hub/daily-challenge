# System Patterns

**Architecture Overview:**

- FastAPI backend with modular routers/services
- PostgreSQL database (via Docker) and SQLAlchemy ORM
- Redis for rate limiting, caching, and message broker
- Celery for asynchronous task processing and scheduling
- JWT-based authentication with role-based access control

**Key Patterns:**

- ESM modules in Node; Python uses packages and modules structure
- Dependency injection for DB sessions in FastAPI
- Repository/service pattern for data access
- Event-driven alerts for low-content triggers
- Hierarchical tag model with parent-child relationships
  - Tags organized in a multi-level hierarchy (e.g., Languages → Python)
  - Tag types for classification (language, skill_level, topic, framework, tool, domain, concept)
  - Self-referential relationship for parent-child connections
  - Bidirectional navigation between parent and children
  - Serialization includes child tags IDs for seamless frontend consumption
- Centralized tag management separates tag creation from problem creation
  - Only existing/approved tags are associated with problems
  - User-suggested tags are stored in problem_metadata for admin review
  - TagRepository and ProblemRepository enforce case-insensitive, session-safe tag lookups
  - Admin UI planned for reviewing and approving pending tags
- Consistent API router structure with common prefix
- Standardized response models for all endpoints
  - Consistent error format with proper HTTP status codes
  - Detailed validation error messages for client debugging
  - Schema-driven serialization with explicit field inclusion/exclusion
  - Proper handling of nested relationships in responses
- Task queue separation by domain (emails, content, default)
- Periodic task scheduling via Celery Beat
- Rate limiting for public API endpoints
- Explicit serialization pattern for SQLAlchemy models with relationships.
- API endpoints must never return raw SQLAlchemy objects or lists.
- Contract-first development: schemas drive serialization.

**Design Decisions:**

- Use Docker for local DB consistency
- Use Alembic for migrations
- Memory Bank structure for preserving context
- Route organization with /api prefix and resource-based endpoints
- Enum handling in database with appropriate migrations
- Authentication applied at router level for consistent security
- Redis-based distributed rate limiting with fallback mechanism
- Background processing for resource-intensive tasks using Celery
- Separate queue structure to isolate different types of tasks
- Custom base task class with enhanced logging and error handling
- Explicit task naming for better monitoring and debugging

**Celery Task Architecture:**

- Email Tasks: Responsible for user communication (welcome emails, daily challenges)
- Content Tasks: Handle problem generation, selection, and delivery scheduling
- Maintenance Tasks: System health monitoring and housekeeping
- Task organization by domain to maintain clear boundaries
- Task retry policies with exponential backoff for handling transient failures
- Task monitoring via Flower dashboard for operational visibility
- Regular health checks to ensure system components are functioning properly
