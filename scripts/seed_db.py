

import os
import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.db.models.problem import Problem, VettingTier, DifficultyLevel, ProblemStatus
from app.db.models.tag import Tag, TagType
from app.db.models.content_source import ContentSource, SourcePlatform, ProcessingStatus
from app.db.models.user import User, SubscriptionStatus
from app.core.security import get_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Load DB URL from env or use default (dev)
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dcq_user:dcq_pass@localhost:5433/dcq_db")

# To seed the test database, uncomment the following line and comment out the dev DB line above:

DATABASE_URL = "postgresql://dcq_test_user:dcq_test_pass@localhost:5434/dcq_test_db"
def parse_enum(enum_cls, value):
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError:
        # Try by name (for legacy or alternate JSON)
        for member in enum_cls:
            if member.name == value:
                return member
        raise

def parse_datetime(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None

def seed_tags(session, tags_json_path="test_tags.json"):
    if not os.path.exists(tags_json_path):
        print(f"No {tags_json_path} found, skipping tag seeding.")
        return
    with open(tags_json_path) as f:
        tags = json.load(f)
    for tag in tags:
        if not session.query(Tag).filter_by(name=tag["name"]).first():
            session.add(Tag(
                name=tag["name"],
                description=tag.get("description"),
                tag_type=parse_enum(TagType, tag.get("tag_type")),
                is_featured=tag.get("is_featured", False),
                is_private=tag.get("is_private", False),
                parent_tag_id=tag.get("parent_tag_id")
            ))
    session.commit()
    print("Seeded tags.")

def seed_users_via_api(users_json_path="test_users.json", api_url="http://localhost:8000/api/auth/register"):
    import subprocess
    import time
    if not os.path.exists(users_json_path):
        print(f"No {users_json_path} found, skipping API user seeding.")
        return
    with open(users_json_path) as f:
        users = json.load(f)
    for user in users:
        # Prepare JSON payload
        user_payload = {
            "email": user["email"],
            "password": user["password"]
        }
        if "full_name" in user:
            user_payload["full_name"] = user["full_name"]
        # Remove user if exists (using direct DB call)
        # This is handled outside this function
        # Use curl to register user
        cmd = [
            "curl", "-X", "POST", api_url,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(user_payload)
        ]
        print(f"Registering user via API: {user_payload['email']}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"API response: {result.stdout.strip()}")
        except Exception as e:
            print(f"Error registering user {user_payload['email']}: {e}")
        time.sleep(0.5)  # slight delay to avoid race conditions
    print("Seeded users via API.")

def remove_all_users(session):
    session.query(User).delete()
    session.commit()
    print("Removed all users from test DB.")

def seed_content_sources(session, sources_json_path="test_content_sources.json"):
    if not os.path.exists(sources_json_path):
        print(f"No {sources_json_path} found, skipping content source seeding.")
        return
    with open(sources_json_path) as f:
        sources = json.load(f)
    for source in sources:
        if not session.query(ContentSource).filter_by(source_identifier=source["source_identifier"]).first():
            session.add(ContentSource(
                source_platform=parse_enum(SourcePlatform, source.get("source_platform")),
                source_identifier=source["source_identifier"],
                source_url=source.get("source_url"),
                source_title=source.get("source_title"),
                raw_data=source.get("raw_data"),
                processed_text=source.get("processed_text"),
                source_tags=source.get("source_tags"),
                notes=source.get("notes"),
                processing_status=parse_enum(ProcessingStatus, source.get("processing_status")),
                ingested_at=parse_datetime(source.get("ingested_at")),
                processed_at=parse_datetime(source.get("processed_at"))
            ))
    session.commit()
    print("Seeded content sources.")

def seed_problems(session, problems_json_path="test_problems.json"):
    if not os.path.exists(problems_json_path):
        print(f"No {problems_json_path} found, skipping problem seeding.")
        return
    with open(problems_json_path) as f:
        problems = json.load(f)
    for problem in problems:
        if not session.query(Problem).filter_by(title=problem["title"]).first():
            session.add(Problem(
                title=problem["title"],
                description=problem.get("description", "Seeded problem."),
                solution=problem.get("solution"),
                vetting_tier=parse_enum(VettingTier, problem.get("vetting_tier")),
                status=parse_enum(ProblemStatus, problem.get("status")),
                difficulty=parse_enum(DifficultyLevel, problem.get("difficulty")),
                approved_at=parse_datetime(problem.get("approved_at")),
                content_source_id=problem.get("content_source_id")
            ))
    session.commit()
    print("Seeded problems.")

def main():
    print(f"Using database URL: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        remove_all_users(session)
        session.close()  # Close DB session before API calls
        seed_users_via_api()
        session = Session()  # Reopen for further seeding
        seed_tags(session)
        seed_content_sources(session)
        seed_problems(session)
    except IntegrityError as e:
        print(f"IntegrityError: {e}")
        session.rollback()
    finally:
        session.close()
    print("Database seeding complete.")

if __name__ == "__main__":
    main()
