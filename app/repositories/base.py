from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.sql.expression import Select
from fastapi.encoders import jsonable_encoder
from uuid import UUID
import uuid as uuid_pkg

from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository providing CRUD operations for SQLAlchemy models.
    To be inherited by specific model repositories.
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository with model class and database session.
        
        Args:
            model: The SQLAlchemy model class
            db: SQLAlchemy database session
        """
        self.model = model
        self.db = db

    def get(self, id: UUID) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: ID of the record to retrieve

        Returns:
            The model instance or None if not found
        """
        # Use joinedload to eagerly load relationships defined in the model
        if hasattr(self.model, 'children'):
            return self.db.query(self.model).options(
                joinedload(self.model.children)
            ).filter(self.model.id == id).first()
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, *, skip: int = 0, limit: int = 100, order_by: str = None, order_direction: str = "asc", **filters
    ) -> List[ModelType]:
        """
        Get multiple records with optional pagination, sorting and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order results by (e.g., "created_at", "id", etc.)
            order_direction: Direction to order results ("asc" or "desc")
            **filters: Additional filters to apply
                Special filter formats:
                - field__lt: Less than
                - field__gt: Greater than
                - field__lte: Less than or equal
                - field__gte: Greater than or equal
                - field__ilike: Case-insensitive partial match (use %wildcards% in value)
                - field__like: Case-sensitive partial match (use %wildcards% in value)
                - field__in: Check if value is in a list

        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Apply eager loading for children relationship if it exists
        if hasattr(self.model, 'children'):
            query = query.options(joinedload(self.model.children))
            
        # Apply any additional filters passed
        for filter_key, value in filters.items():
            # Skip None values
            if value is None:
                continue
                
            # Check if this is a special filter with operator
            if '__' in filter_key:
                field_name, operator = filter_key.split('__', 1)
                
                # Make sure the field exists on the model
                if not hasattr(self.model, field_name):
                    print(f"Warning: Field {field_name} does not exist on model {self.model.__name__}")
                    continue
                    
                field = getattr(self.model, field_name)
                
                # Apply the appropriate operator
                if operator == 'lt':
                    query = query.filter(field < value)
                elif operator == 'lte':
                    query = query.filter(field <= value)
                elif operator == 'gt':
                    query = query.filter(field > value)
                elif operator == 'gte':
                    query = query.filter(field >= value)
                elif operator == 'ilike':
                    query = query.filter(field.ilike(value))
                elif operator == 'like':
                    query = query.filter(field.like(value))
                elif operator == 'in':
                    query = query.filter(field.in_(value))
                else:
                    print(f"Warning: Unknown operator {operator} for field {field_name}")
            else:
                # Direct attribute filter (equality)
                if hasattr(self.model, filter_key):
                    query = query.filter(getattr(self.model, filter_key) == value)
                else:
                    print(f"Warning: Field {filter_key} does not exist on model {self.model.__name__}")

        # Apply ordering if specified
        if order_by and hasattr(self.model, order_by):
            field = getattr(self.model, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field.asc())
        else:
            # Default ordering by id if no specific ordering is requested
            query = query.order_by(self.model.id.asc())
                    
        return query.offset(skip).limit(limit).all()
    
    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new object in the database.

        Args:
            obj_in: Create schema instance
            
        Returns:
            The created model instance
        """
        try:
            print(f"Creating {self.model.__name__} with data: {obj_in}")
            obj_in_data = jsonable_encoder(obj_in)
            print(f"Encoded data: {obj_in_data}")
            
            # Handle subscription_status specially if this is User model
            if hasattr(self.model, 'subscription_status') and 'subscription_status' in obj_in_data:
                from app.db.models.user import SubscriptionStatus
                ss = obj_in_data['subscription_status']
                print(f"Processing subscription_status: {ss}, type: {type(ss)}")
                if isinstance(ss, str):
                    try:
                        # Try to convert string to enum
                        obj_in_data['subscription_status'] = SubscriptionStatus(ss)
                        print(f"Converted to enum: {obj_in_data['subscription_status']}")
                    except ValueError as e:
                        print(f"Error converting subscription_status: {e}")
                        # Use a default value
                        obj_in_data['subscription_status'] = SubscriptionStatus.active
            
            # Handle password field conversion for User model
            if hasattr(self.model, 'hashed_password') and 'password' in obj_in_data:
                from app.core.security import get_password_hash
                # Convert password to hashed_password
                obj_in_data['hashed_password'] = get_password_hash(obj_in_data.pop('password'))
                print(f"Converted password to hashed_password")
            
            # Handle UUID fields conversion (particularly important for SQLite)
            uuid_fields = ['user_id', 'problem_id', 'id', 'parent_tag_id', 'content_source_id']
            for field in uuid_fields:
                if field in obj_in_data and isinstance(obj_in_data[field], str):
                    try:
                        obj_in_data[field] = uuid_pkg.UUID(obj_in_data[field])
                        print(f"Converted {field} from string to UUID: {obj_in_data[field]}")
                    except (ValueError, AttributeError) as e:
                        print(f"Error converting {field} to UUID: {e}")
            
            # Create a clean data dictionary without any attributes that don't exist on the model
            model_fields = {column.key for column in self.model.__table__.columns}
            print(f"Available model fields: {model_fields}")
            print(f"Input data before cleaning: {obj_in_data}")
            
            # Debug check for specific fields
            if 'full_name' in obj_in_data:
                print(f"full_name value before cleaning: {obj_in_data['full_name']}")
            
            cleaned_data = {k: v for k, v in obj_in_data.items() if k in model_fields or k == 'password'}
            
            # Debug after cleaning
            print(f"Cleaned data for model creation: {cleaned_data}")
            if 'full_name' in obj_in_data and 'full_name' not in cleaned_data:
                print(f"WARNING: full_name was in input data but removed during cleaning!")
                # Force include it if it's in the User model
                if self.model.__name__ == 'User':
                    cleaned_data['full_name'] = obj_in_data['full_name']
                    print(f"Manually added full_name back: {cleaned_data['full_name']}")
            
            db_obj = self.model(**cleaned_data)  # type: ignore
            print(f"Created object before commit: {db_obj.__dict__}")
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            print(f"Created object after commit: {db_obj.__dict__}")
            return db_obj
        except Exception as e:
            import traceback
            print(f"Error in create method for {self.model.__name__}: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            self.db.rollback()
            raise
    
    def update(
        self, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            db_obj: The database object to update
            obj_in: Update data either as schema or dict
            
        Returns:
            The updated model instance
        """
        # Skip full serialization which can cause recursion errors with complex relationships
        # Instead, just get the table columns directly
        model_fields = {column.key for column in self.model.__table__.columns}
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else jsonable_encoder(obj_in)
            
        # Only update fields that are model columns and are in the update data
        for field in model_fields:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, *, id: Any) -> ModelType:
        """
        Delete a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            The deleted model instance
        """
        # Use Session.get() instead of Query.get() for SQLAlchemy 2.0 compatibility
        obj = self.db.get(self.model, id)
        if obj is None:
            raise ValueError(f"{self.model.__name__} with id {id} not found")
        self.db.delete(obj)
        self.db.commit()
        return obj
    
    def count(self, filters: Dict = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            filters: Optional dictionary of filters
            
        Returns:
            Count of matching records
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for attr, value in filters.items():
                if hasattr(self.model, attr):
                    query = query.where(getattr(self.model, attr) == value)
        
        return self.db.execute(query).scalar() or 0
