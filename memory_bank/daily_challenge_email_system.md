# Daily Challenge Email System

## Overview
The Daily Challenge Email System delivers coding problems to users on a daily basis and sends solutions 24 hours later. The system selects problems based on users' tag preferences, utilizing the tag hierarchy to provide relevant content.

## Core Components

### 1. Two-Phase Email Delivery
- **Problem Email**: Sent to all active, verified users
- **Solution Email**: Sent 24 hours after the problem
- **Future Premium Feature**: Solutions will eventually be limited to premium users

### 2. User Eligibility
- All active, email-verified users receive daily problems
- Regular users cannot opt out
- Premium users (future) will have delivery preferences

### 3. Problem Selection
- Based on users' subscribed tags
- Includes problems tagged with child tags (hierarchical relationship)
- Example: User subscribed to "Tree" receives "Binary Tree" and "AST" problems

## Database Schema Changes

### User Model Updates
```python
# Add to existing User model
last_problem_sent_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=True)
last_problem_sent_at = Column(DateTime(timezone=True), nullable=True)
is_subscribed_to_solutions = Column(Boolean, default=True, nullable=False)
```

### Premium User Preferences (Future)
```python
class PremiumUserPreferences(BaseModel):
    __tablename__ = "premium_user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    preferred_delivery_time = Column(Time, default=time(8, 0), nullable=False)
    preferred_days = Column(ARRAY(String), default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], nullable=False)
    difficulty_preference = Column(String, default="mixed", nullable=False)
    tags_weightage = Column(JSON, default={}, nullable=False)
```

## Implementation Tasks

### Phase 1: Core Functionality
1. Update User model with tracking fields
2. Create problem selection algorithm with tag hierarchy support
3. Implement problem email scheduler
4. Implement solution email scheduler (24-hour delay)
5. Modify email templates for separate problem/solution emails

### Phase 2: Tracking & Admin
1. Add email delivery tracking
2. Create admin endpoints for monitoring
3. Implement basic analytics

### Phase 3: Premium Features (Future)
1. Implement PremiumUserPreferences model
2. Add preference-based delivery for premium users
3. Restrict solutions to premium users
4. Add advanced personalization

## Technical Approach

### Schedulers
- **Problem Scheduler**: Runs daily, selects users and problems, sends emails
- **Solution Scheduler**: Runs daily, finds users who received problems 24 hours ago

### Problem Selection Algorithm
1. Get user's subscribed tags
2. Expand to include child tags
3. Find problems matching these tags that haven't been sent to the user
4. Prioritize based on difficulty level and relevance

### Email Templating
- Problem email: Challenge description and context
- Solution email: Complete solution with explanation
