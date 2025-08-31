# Daily Challenge Platform

A modern coding challenge platform for daily skill improvement with AI-powered content generation.

## Overview

Daily Challenge is a platform designed to help users improve their coding skills through daily challenges. The platform leverages AI content generation to create diverse, high-quality coding problems across various programming languages, frameworks, and difficulty levels.

## System Architecture

The platform follows a modern FastAPI-based architecture with the following key components:

### Backend Components

- **FastAPI Application**: Core REST API providing all application endpoints
- **PostgreSQL Database**: Persistent storage for all application data
- **Redis**: Message broker for task queues and caching
- **Celery Workers**: Distributed task processing system
  - `celery_worker_content`: AI-powered content generation pipeline  
  - `celery_worker_emails`: Email processing tasks
  - `celery_worker_default`: General application tasks
- **Celery Beat**: Scheduler for periodic tasks
- **Flower**: Monitoring dashboard for Celery tasks

### Key Features

1. **AI-Powered Content Generation**
   - Multi-provider LLM integration (Claude, Gemini)
   - Content sources from GitHub, Stack Overflow, and more
   - Tag-based content organization with hierarchical system
   - Automated content quality validation
   
2. **User Management**
   - JWT-based authentication system
   - Role-based access control
   - User subscription management

3. **Content Management**
   - Problem CRUD operations with tagging
   - Hierarchical tag system with parent-child relationships
   - Content delivery and scheduling

4. **Infrastructure**
   - Docker-based deployment
   - Comprehensive logging system
   - Monitoring and observability tools

## Content Pipeline

The AI-powered content pipeline is a core feature of the platform, leveraging LLMs to generate high-quality coding challenges.

### Pipeline Components

1. **Content Sources**
   - GitHub API integration for code samples
   - Stack Overflow API for real-world problems and solutions
   - Extensible design for adding more sources

2. **AI Providers**
   - Claude API integration for problem generation and validation
   - Gemini API support as an alternative
   - Provider-agnostic design for easy expansion

3. **Problem Processing**
   - JSON parsing and validation
   - Automatic tagging and categorization
   - Quality control checks
   - Tag hierarchy assignment

### Tag Hierarchy System

The platform uses a sophisticated tag hierarchy system for better content organization:

- **Parent-Child Relationships**: Tags can have parent tags and child tags
- **Category Organization**: Primary categories include languages, frameworks, concepts, and difficulty levels
- **Automatic Categorization**: AI-generated tags are automatically mapped to standard categories
- **Hierarchy Example**:
  - `Languages` → `JavaScript` → `React`
  - `Code Quality` → `Linting` → `ESLint`

## Setup and Development

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- PostgreSQL 13+
- Redis

### Environment Configuration

1. Copy the `.env.example` file to `.env` and set required environment variables:
   ```
   cp .env.example .env
   ```

2. Configure API keys for LLM providers:
   - `ANTHROPIC_API_KEY`: Claude API key
   - `GEMINI_API_KEY`: Google Gemini API key

### Running the Application

1. Start the main application:
   ```
   docker-compose up -d
   ```

2. Start the Celery workers for content pipeline:
   ```
   docker-compose -f docker-compose.celery.yml up -d
   ```

3. Access the API at `http://localhost:8000/api`

4. Access the API documentation at `http://localhost:8000/docs`

5. Access the Flower dashboard at `http://localhost:5555`

### Development Workflow

1. Install development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```

2. Run migrations:
   ```
   alembic upgrade head
   ```

3. Run tests:
   ```
   pytest
   ```

## Content Pipeline Scripts

### Initial Tag Hierarchy Setup

Before running the content pipeline, set up the tag hierarchy system:

```bash
python scripts/setup_tag_hierarchy.py
```

This script:
1. Creates parent categories (languages, difficulty, code quality, etc.)
2. Establishes parent-child relationships between tags
3. Standardizes tag names for consistency

### Fix Tag Parents

To repair or update existing tag parent-child relationships:

```bash
python scripts/fix_tag_parents.py
```

This SQL-based script ensures all tags have proper parent-child relationships established, especially useful when you have existing tags that need organization.

### Trigger Content Pipeline

To generate problem content using the AI pipeline:

```bash
python scripts/trigger_content_pipeline.py
```

This script:
1. Connects to the Celery task system
2. Fetches content from GitHub (configured for Microsoft/VSCode repo)
3. Generates a problem using Claude AI
4. Validates the problem structure
5. Saves the problem to the database with proper tag hierarchy

### Content Source Testing

To test specific content sources directly:

```bash
# Test GitHub integration
python scripts/test_content_sources_filtering.py --source github

# Test Stack Overflow integration
python scripts/test_content_sources_filtering.py --source stackoverflow
```

### AI Provider Testing

To directly test the Claude AI provider:

```bash
python scripts/direct_test_claude.py
```

To test the Gemini AI provider:

```bash
python scripts/direct_test_gemini.py
```

## Monitoring

- **Logs**: Available in `./logs` directory with JSON formatting
- **Celery Tasks**: Monitor via Flower dashboard at `http://localhost:5555`
- **Database**: Connect directly or use PostgreSQL admin tools at `localhost:5433`

## Architecture Decisions

### Asynchronous Processing

The system uses Celery for handling long-running tasks like content generation to ensure the API remains responsive. The content pipeline operates asynchronously, with results stored in the database.

### Database Operations

The system supports both synchronous and asynchronous database operations:
- FastAPI endpoints use async database sessions for non-blocking operation
- Celery tasks use synchronous database operations to avoid event loop conflicts

### Logging System

The application uses Python's standard logging with JSON formatting to ensure consistent logs across all components, with request ID tracking for distributed tracing.

### Error Handling

Robust error handling is implemented throughout the application, with standardized error responses and comprehensive logging.

## Future Enhancements

1. Multi-LLM support with automatic failover
2. Enhanced content quality control and review workflow
3. User engagement metrics and analytics
4. Expanded content sources beyond GitHub and Stack Overflow
5. Fine-tuning of LLMs based on user feedback
