import pytest
from datetime import datetime, timedelta
from app.db.models.delivery_log import DeliveryStatus, DeliveryChannel
from app.schemas.delivery_log import DeliveryLogCreate, DeliveryLogUpdate
from conftest import TestDeliveryLog


def test_get_by_user(db_session, delivery_log_repository, sample_delivery_log, sample_user):
    """Test retrieving delivery logs for a specific user."""
    logs = delivery_log_repository.get_by_user(user_id=sample_user.id)
    assert len(logs) == 1
    assert logs[0].id == sample_delivery_log.id
    assert logs[0].user_id == sample_user.id


def test_get_by_user_nonexistent(db_session, delivery_log_repository):
    """Test retrieving delivery logs for a nonexistent user returns empty list."""
    logs = delivery_log_repository.get_by_user(user_id=9999)
    assert logs == []


def test_get_by_problem(db_session, delivery_log_repository, sample_delivery_log, sample_problem):
    """Test retrieving delivery logs for a specific problem."""
    logs = delivery_log_repository.get_by_problem(problem_id=sample_problem.id)
    assert len(logs) == 1
    assert logs[0].id == sample_delivery_log.id
    assert logs[0].problem_id == sample_problem.id


def test_get_by_problem_nonexistent(db_session, delivery_log_repository):
    """Test retrieving delivery logs for a nonexistent problem returns empty list."""
    logs = delivery_log_repository.get_by_problem(problem_id=9999)
    assert logs == []


def test_get_by_status(db_session, delivery_log_repository, sample_delivery_log):
    """Test retrieving delivery logs by status."""
    # Create a second delivery log with different status
    from app.schemas.delivery_log import DeliveryLogCreate
    import uuid
    
    # Ensure the IDs are UUID objects and not strings
    user_id = sample_delivery_log.user_id
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
        
    problem_id = sample_delivery_log.problem_id
    if isinstance(problem_id, str):
        problem_id = uuid.UUID(problem_id)
    
    second_log_in = DeliveryLogCreate(
        user_id=user_id,
        problem_id=problem_id,
        status="failed",
        delivery_channel="email",
        meta={"error": "Connection timeout"}
    )
    second_log = delivery_log_repository.create(second_log_in)
    
    # Test retrieving delivery logs by status
    scheduled_logs = delivery_log_repository.get_by_status(status="scheduled")
    assert any(log.id == sample_delivery_log.id for log in scheduled_logs), "Sample delivery log not found in scheduled logs"
    failed_logs = delivery_log_repository.get_by_status(status="failed")
    assert any(log.id == second_log.id for log in failed_logs), "Second log not found in failed logs"


def test_get_by_date_range(db_session, delivery_log_repository, sample_delivery_log):
    """Test retrieving delivery logs within a date range."""
    # Ensure the sample delivery log has a delivery date
    now = datetime.utcnow()
    sample_delivery_log.delivered_at = now
    db_session.commit()
    
    # Create a second delivery log with different delivery date
    yesterday = now - timedelta(days=1)
    second_log = TestDeliveryLog(
        user_id=sample_delivery_log.user_id,
        problem_id=sample_delivery_log.problem_id,
        status="delivered",
        delivery_channel="email",
        meta={"channel": "email"},
        delivered_at=yesterday
    )
    db_session.add(second_log)
    db_session.commit()
    
    # Test retrieving delivery logs for today only
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1) - timedelta(microseconds=1)
    
    today_logs = delivery_log_repository.get_by_date_range(
        start_date=today_start,
        end_date=today_end
    )
    assert len(today_logs) == 1
    assert today_logs[0].id == sample_delivery_log.id
    
    # Test retrieving delivery logs for yesterday only
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start - timedelta(microseconds=1)
    
    yesterday_logs = delivery_log_repository.get_by_date_range(
        start_date=yesterday_start,
        end_date=yesterday_end
    )
    assert len(yesterday_logs) == 1
    assert yesterday_logs[0].id == second_log.id
    
    # Test retrieving delivery logs for both days
    two_day_logs = delivery_log_repository.get_by_date_range(
        start_date=yesterday_start,
        end_date=today_end
    )
    assert len(two_day_logs) == 2


def test_get_user_problem_delivery(db_session, delivery_log_repository, sample_delivery_log, sample_user, sample_problem):
    """Test retrieving the delivery log for a specific user and problem combination."""
    log = delivery_log_repository.get_user_problem_delivery(
        user_id=sample_user.id,
        problem_id=sample_problem.id
    )
    assert log is not None
    assert log.id == sample_delivery_log.id
    assert log.user_id == sample_user.id
    assert log.problem_id == sample_problem.id


def test_get_user_problem_delivery_nonexistent(db_session, delivery_log_repository, sample_user):
    """Test retrieving a nonexistent user-problem delivery log returns None."""
    log = delivery_log_repository.get_user_problem_delivery(
        user_id=sample_user.id,
        problem_id=9999
    )
    assert log is None


def test_count_by_status(db_session, delivery_log_repository, sample_delivery_log):
    """Test counting delivery logs by status."""
    from app.schemas.delivery_log import DeliveryLogCreate
    
    # Print the sample delivery log that comes from the fixture
    print(f"\n>>> Sample delivery log from fixture: id={sample_delivery_log.id}, status={sample_delivery_log.status}")
    
    import uuid
    
    # Ensure the IDs are UUID objects and not strings
    user_id = sample_delivery_log.user_id
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
        
    problem_id = sample_delivery_log.problem_id
    if isinstance(problem_id, str):
        problem_id = uuid.UUID(problem_id)
    
    logs = [
        DeliveryLogCreate(
            user_id=user_id,
            problem_id=problem_id,
            status="delivered",
            delivery_channel="email",
            meta={"channel": "email"}
        ),
        DeliveryLogCreate(
            user_id=user_id,
            problem_id=problem_id,
            status="delivered",
            delivery_channel="slack",
            meta={"channel": "slack"}
        ),
        DeliveryLogCreate(
            user_id=user_id,
            problem_id=problem_id,
            status="failed",
            delivery_channel="email",
            meta={"error": "User not found"}
        ),
        DeliveryLogCreate(
            user_id=user_id,
            problem_id=problem_id,
            status="failed",
            delivery_channel="email",
            meta={"error": "Connection timeout"}
        )
    ]
    
    created_logs = []
    for log_in in logs:
        created_log = delivery_log_repository.create(log_in)
        created_logs.append(created_log)
        print(f">>> Created log: id={created_log.id}, status={created_log.status}")
    
    # Verify logs are in the database by doing a direct query
    all_logs = db_session.query(delivery_log_repository.model).all()
    print(f">>> Total logs in database: {len(all_logs)}")
    for log in all_logs:
        print(f">>> Log in DB: id={log.id}, status={log.status}")
    
    # Test counting by status
    counts = delivery_log_repository.count_by_status()
    print(f">>> Status counts from repository: {counts}")
    
    scheduled_count = counts.get("scheduled")
    delivered_count = counts.get("delivered")
    failed_count = counts.get("failed")
    assert scheduled_count == 1  # One log with status "scheduled" from fixture
    assert delivered_count == 2  # Two logs with status "delivered" from test
    assert failed_count == 2     # Two logs with status "failed" were created
