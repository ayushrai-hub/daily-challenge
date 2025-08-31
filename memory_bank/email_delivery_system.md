# Email Delivery System

## Overview

The Email Delivery System is a core component of the Daily Challenge application, responsible for reliably delivering daily engineering challenges to subscribed users. It serves as the primary delivery channel in the MVP, with a focus on providing a convenient and habitual way for engineers to engage with learning material.

## Architecture

The system follows an asynchronous processing architecture with these key components:

1. **Email Queue**: Persists email requests with tracking information
2. **Celery Tasks**: Processes queued emails and schedules daily deliveries
3. **Email Service**: Interfaces with Resend API for actual delivery
4. **Delivery Logs**: Records all delivery attempts and their outcomes
5. **API Endpoints**: Manages email operations and provides status information

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ API Endpoints │────▶│  Email Queue  │────▶│ Celery Worker │────▶│  Resend API   │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
                              │                     │                      │
                              │                     │                      │
                              ▼                     ▼                      ▼
                      ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
                      │ Delivery Logs │     │   Logging     │     │   Webhooks    │
                      └───────────────┘     └───────────────┘     └───────────────┘
```

## Core Requirements

### 1. Functionality
- Deliver one engineering challenge (problem statement and solution) daily to each subscribed user
- Support onboarding, welcome, and transactional emails
- Ensure consistent delivery timing for habit formation (8:00 AM UTC default)

### 2. Content and Formatting
- Present challenges with clarity and readability
- Use high-quality HTML formatting optimized for email clients
- Ensure mobile-friendly responsive design
- Include unsubscribe options and preference management links
- Source content from approved, high-quality problems (Tier 1 preferred)

### 3. Personalization and Relevance
- Deliver challenges relevant to user's selected tags
- Implement fallback logic for when exact matches aren't available:
  - First: Select undelivered problems matching user tags
  - Second: Allow repeats after 30 days if necessary
  - Third: Default to any approved problem
- Avoid sending the same problem to a user multiple times

### 4. Reliability and Monitoring
- Target email delivery success rate >99.5%
- Implement SPF, DKIM, and DMARC for optimal deliverability
- Comprehensive logging of all delivery attempts and failures
- Monitor delivery rates, open rates, and ESP errors
- Graceful handling of delivery failures with retry mechanisms

## Technical Implementation

### Email Queue Model
The system uses a dedicated `EmailQueue` table to store pending and processed emails:
- Tracks recipient, subject, content, and metadata
- Records status (pending, sent, failed, cancelled)
- Stores delivery timestamps and error messages
- Links to users and problems for personalization

### Celery Tasks
- `process_pending_emails`: Runs every minute to process due emails in the queue
- `send_daily_challenge`: Sends a specific challenge to a single user
- `schedule_daily_delivery`: Runs daily to select appropriate challenges and queue them for all users

### Email Service
- Interface with Resend API for actual delivery
- Input validation for emails before processing
- Template rendering for consistent formatting
- Webhook handling for delivery events and tracking

### API Endpoints
- `POST /api/emails/queue`: Queue an email for future delivery
- `GET /api/emails/status/{tracking_id}`: Check status of a queued email
- `GET /api/emails/`: List and filter queued emails (admin)
- `DELETE /api/emails/{email_id}`: Cancel a pending email

## Performance Targets
- Email Delivery Success Rate: >99.5%
- Target Open Rate: >30-40%
- Target Unsubscribe Rate: <0.5%
- Email Processing Time: <5 minutes from scheduled time

## Future Enhancements
- User-specific delivery time preferences
- A/B testing of email templates and subjects
- Additional delivery channels (Slack)
- Enhanced tracking of user engagement metrics
- Automated retry strategies for failed deliveries

---

## Celery Email Delivery System Operations Guide

### Overview
Celery is used to process and deliver emails asynchronously in the Daily Challenge platform. It works in tandem with Redis (as the broker), PostgreSQL (for the email queue), and the Resend API (for actual email sending). Flower is used for monitoring.

### Core Commands

#### 1. Start All Components (Recommended for Dev)
```bash
./scripts/run_celery.sh all
```
- Starts Celery workers, Celery Beat (scheduler), and Flower dashboard.
- Flower available at: http://localhost:5555

#### 2. Start Worker for Email Queue
```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info --queues=emails
```
- Processes queued emails (tasks: `process_pending_emails`, etc.)

#### 3. Start Celery Beat (Scheduler)
```bash
celery -A app.core.celery_app.celery_app beat --loglevel=info
```
- Schedules periodic tasks (e.g., `process_pending_emails` every minute)

#### 4. Start Flower Dashboard
```bash
celery -A app.core.celery_app.celery_app flower --port=5555
```
- Web UI for monitoring tasks, worker status, and failures.

### How It Works
- **Enqueue Email:** Insert a row into `email_queue` (via API or DB).
- **Worker:** Picks up `pending` emails, sends them using `EmailService` (Resend API), updates status to `sent` or `failed`.
- **Beat:** Triggers `process_pending_emails` every minute.
- **Monitoring:** Use Flower to view live status, errors, and task logs.

### Operational Tips
- Only emails with `status = 'pending'` are processed. Failed emails require manual reset or retry logic.
- Logs are written to console and `./logs` directory.
- Environment/configuration is loaded via `.env` and Pydantic `Settings`.
- Slack notifications and error alerts are integrated for delivery events.

### Troubleshooting
- **No emails sent?** Check worker logs, Resend API key, and queue status.
- **Task not running?** Ensure Beat and Worker are both running.
- **Flower 401 error?** Set `FLOWER_UNAUTHENTICATED_API=1` in your environment for API access.
- **.env errors?** Ensure no spaces or shell-incompatible characters in `.env` values (esp. email addresses).

### Example: Manual Email Enqueue (SQL)
```sql
INSERT INTO email_queue (user_id, email_type, recipient, subject, html_content, text_content, status, scheduled_for)
VALUES (1, 'welcome', 'your@email.com', 'Welcome!', '<h1>Hi!</h1>', 'Hi!', 'pending', NOW());
```

### Example: Manual Email Enqueue (API)
```bash
curl -X POST http://localhost:8000/api/emails/queue \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "email_type": "welcome",
    "recipient": "your@email.com",
    "subject": "Welcome!",
    "html_content": "<h1>Hi!</h1>",
    "text_content": "Hi!"
  }'
```

---

For more details, see: `memory_bank/email_delivery_system.md`, `memory_bank/systemPatterns.md`, and `memory_bank/activeContext.md`.
