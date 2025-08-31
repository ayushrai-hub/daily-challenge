from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import select, func

from app.db.models.content_source import ContentSource, SourcePlatform
from app.schemas.content_source import ContentSourceCreate, ContentSourceUpdate
from app.repositories.base import BaseRepository


class ContentSourceRepository(BaseRepository[ContentSource, ContentSourceCreate, ContentSourceUpdate]):
    """Repository for ContentSource model providing CRUD operations and source-specific queries."""
    
    def __init__(self, db: Session):
        super().__init__(model=ContentSource, db=db)
    
    def get_by_source_identifier(self, source_identifier: str) -> Optional[ContentSource]:
        """
        Get a content source by its source identifier.
        
        Args:
            source_identifier: Source identifier to search for
            
        Returns:
            ContentSource instance or None if not found
        """
        return self.db.query(ContentSource).filter(
            ContentSource.source_identifier == source_identifier
        ).first()
        
    def get_by_platform_and_identifier(self, platform: SourcePlatform, source_identifier: str) -> Optional[ContentSource]:
        """
        Get a content source by its platform and source identifier combination.
        This is useful to check for violations of the unique constraint before attempting to create.
        
        Args:
            platform: Source platform to filter by
            source_identifier: Source identifier to search for
            
        Returns:
            ContentSource instance or None if not found
        """
        return self.db.query(ContentSource).filter(
            ContentSource.source_platform == platform,
            ContentSource.source_identifier == source_identifier
        ).first()
    
    def get_by_platform(self, platform: SourcePlatform, skip: int = 0, limit: int = 100) -> List[ContentSource]:
        """
        Get content sources by platform.
        
        Args:
            platform: Source platform to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of ContentSource instances
        """
        return self.db.query(ContentSource).filter(
            ContentSource.source_platform == platform
        ).offset(skip).limit(limit).all()
    
    def get_with_problems(self, skip: int = 0, limit: int = 100) -> List[ContentSource]:
        """
        Get content sources that have generated problems.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of ContentSource instances
        """
        return self.db.query(ContentSource).filter(
            ContentSource.problems.any()
        ).offset(skip).limit(limit).all()
    
    def count_by_platform(self) -> Dict[str, int]:
        """
        Count content sources by platform.
        
        Returns:
            Dictionary with platform names as keys and counts as values
        """
        result = {}
        
        # Initialize counts for all platforms to 0
        for platform in SourcePlatform:
            result[platform.value] = 0
            
        query = self.db.query(
            ContentSource.source_platform,
            func.count(ContentSource.id)
        ).group_by(ContentSource.source_platform).all()
        
        for platform, count in query:
            result[platform.value] = count
            
        return result
