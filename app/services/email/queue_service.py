from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.email_queue import EmailQueue
from app.schemas.email import EmailCreate
from uuid import UUID

class EmailQueueService:
    @staticmethod
    def enqueue_email(db: Session, email_data: EmailCreate) -> EmailQueue:
        email = EmailQueue(
            user_id=email_data.user_id,
            email_type=email_data.email_type,
            recipient=email_data.recipient,
            subject=email_data.subject,
            html_content=email_data.html_content,
            text_content=email_data.text_content,
            template_id=email_data.template_id,
            template_data=email_data.template_data,
            # Include problem_id if it exists
            problem_id=email_data.problem_id,
            status="pending"
        )
        db.add(email)
        db.commit()
        db.refresh(email)
        return email

    @staticmethod
    def get_queue(db: Session, skip: int = 0, limit: int = 100) -> List[EmailQueue]:
        return db.query(EmailQueue).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, email_id: UUID) -> Optional[EmailQueue]:
        return db.query(EmailQueue).filter(EmailQueue.id == email_id).first()

    @staticmethod
    def update_status(db: Session, email_id: UUID, status: str) -> Optional[EmailQueue]:
        email = db.query(EmailQueue).filter(EmailQueue.id == email_id).first()
        if email:
            email.status = status
            db.commit()
            db.refresh(email)
        return email

    @staticmethod
    def delete(db: Session, email_id: UUID) -> bool:
        email = db.query(EmailQueue).filter(EmailQueue.id == email_id).first()
        if email:
            db.delete(email)
            db.commit()
            return True
        return False
