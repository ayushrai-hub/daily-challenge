"""
Content processing tasks for the Daily Challenge application.
Handles problem generation, validation, and scheduling.
"""
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from typing import Dict, List, Optional, Union
import time
import random

logger = get_logger()

@celery_app.task(name="generate_daily_challenges", queue="content")
def generate_daily_challenges(
    batch_size: int = 10,
    difficulty_distribution: Optional[Dict[str, float]] = None
) -> Dict[str, Union[bool, int, List]]:
    """
    Generate a batch of daily coding challenges.
    
    Args:
        batch_size: Number of challenges to generate
        difficulty_distribution: Distribution of difficulty levels (e.g., {"easy": 0.5, "medium": 0.3, "hard": 0.2})
        
    Returns:
        Dictionary with status and IDs of the generated problems
    """
    logger.info(f"Generating {batch_size} daily challenges")
    
    # Default difficulty distribution if not provided
    if not difficulty_distribution:
        difficulty_distribution = {"easy": 0.4, "medium": 0.4, "hard": 0.2}
    
    # Simulate problem generation (would use actual database operations in production)
    generated_problems = []
    for i in range(batch_size):
        # Determine difficulty based on distribution
        difficulty = random.choices(
            list(difficulty_distribution.keys()),
            weights=list(difficulty_distribution.values()),
            k=1
        )[0]
        
        # Simulate some processing time
        time.sleep(0.5)
        
        # Simulated problem data
        problem = {
            "id": random.randint(1000, 9999),  # Simulated ID
            "title": f"Example Problem {i+1}",
            "difficulty": difficulty,
            "tags": ["array", "string", "algorithm"],
        }
        generated_problems.append(problem)
    
    logger.info(f"Successfully generated {len(generated_problems)} problems")
    
    return {
        "success": True,
        "generated_count": len(generated_problems),
        "problems": generated_problems,
        "timestamp": time.time(),
    }


@celery_app.task(
    name="schedule_daily_delivery",
    queue="content",
    bind=True,  # Binds the task instance to the first argument (self)
)
def schedule_daily_delivery(self, user_tags: Dict[int, List[str]] = None) -> Dict:
    """
    Match users with appropriate problems based on their tags and schedule delivery.
    
    Args:
        user_tags: Dictionary mapping user IDs to their tag preferences
        
    Returns:
        Dictionary with status and delivery information
    """
    logger.info("Scheduling daily problem delivery")
    
    # Simulated user data if not provided
    if not user_tags:
        user_tags = {
            1: ["arrays", "strings", "algorithms"],
            2: ["database", "system design", "concurrency"],
            3: ["dynamic programming", "graphs", "trees"],
        }
    
    scheduled_deliveries = []
    failed_users = []
    
    # Process each user
    for user_id, tags in user_tags.items():
        try:
            # Simulate matching algorithm to find appropriate problem
            time.sleep(0.2)
            
            # Simulated matched problem
            problem_id = random.randint(1000, 9999)
            
            # Add to delivery queue (in production would call another task)
            scheduled_deliveries.append({
                "user_id": user_id,
                "problem_id": problem_id,
                "tags": tags,
                "scheduled_time": time.time() + 3600,  # Schedule 1 hour in the future
            })
            
            logger.debug(f"Scheduled delivery for user {user_id}, problem {problem_id}")
        except Exception as e:
            logger.error(f"Failed to schedule delivery for user {user_id}: {str(e)}")
            failed_users.append(user_id)
            # Record the failure but continue processing other users
    
    # If many failures, consider retrying the whole task
    if len(failed_users) > len(user_tags) * 0.5:  # If more than 50% failed
        logger.warning(f"High failure rate ({len(failed_users)}/{len(user_tags)}), retrying in 300s")
        # Use exponential backoff for retries with countdown
        raise self.retry(countdown=300)
    
    return {
        "success": len(failed_users) == 0,
        "total_users": len(user_tags),
        "scheduled_count": len(scheduled_deliveries),
        "failed_count": len(failed_users),
        "failed_users": failed_users,
        "timestamp": time.time(),
    }


@celery_app.task(name="validate_problem_solution", queue="content")
def validate_problem_solution(
    problem_id: int,
    solution_code: str,
    language: str
) -> Dict[str, Union[bool, str, int, List]]:
    """
    Validate a user's solution to a problem.
    
    Args:
        problem_id: ID of the problem
        solution_code: User's solution code
        language: Programming language of the solution
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"Validating solution for problem {problem_id}")
    logger.debug(f"Language: {language}, Code length: {len(solution_code)}")
    
    # Simulate solution validation
    time.sleep(2)  # Solution validation might take time
    
    # For demonstration, randomly determine if validation passed
    # In production, would run actual test cases against the solution
    passed = random.random() > 0.3  # 70% chance of passing
    
    # Simulated test results
    test_results = []
    for i in range(5):
        test_results.append({
            "test_case": i + 1,
            "passed": random.random() > 0.2 if passed else random.random() > 0.7,
            "execution_time": random.uniform(0.001, 0.1),
            "memory_usage": random.uniform(1, 10),
        })
    
    return {
        "success": True,
        "validation_passed": passed,
        "problem_id": problem_id,
        "language": language,
        "test_results": test_results,
        "runtime_percentile": random.randint(50, 99) if passed else None,
        "memory_percentile": random.randint(50, 99) if passed else None,
        "timestamp": time.time(),
    }
