"""
Tag Mapping Service

This module provides a service to intelligently map and merge tags in the system.
It handles:
1. Normalization of tag names
2. Mapping similar tags together (case-insensitive and fuzzy matching)
3. Managing parent-child relationships
4. Supporting the hybrid tree/graph structure where tags can have multiple parents
"""

from typing import List, Dict, Optional, Tuple, Set
import string
import re
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid
import logging
from difflib import SequenceMatcher

from app.db.models.tag import Tag, TagType
from app.schemas.tag import TagCreate, TagRead
from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer
from app.core.logging import get_logger

# Use the standardized logging system
logger = get_logger()

# Known technology names and their correct capitalization
TECH_NAME_MAPPINGS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "php": "PHP",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "mongodb": "MongoDB",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "redis": "Redis",
    "react": "React",
    "angular": "Angular",
    "vue": "Vue.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "ruby": "Ruby",
    "rails": "Rails",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "docker": "Docker",
    "kubernetes": "K8s",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "git": "Git",
}

# Tag categories
TAG_CATEGORIES = {
    "Languages": ["python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "php", "ruby", "swift", "kotlin"],
    "Frameworks": ["react", "angular", "vue", "node.js", "express", "django", "flask", "fastapi", "rails"],
    "Databases": ["sql", "mongodb", "postgresql", "mysql", "redis"],
    "Frontend": ["html", "css", "react", "angular", "vue", "typescript"],
    "Backend": ["python", "node.js", "java", "c#", "php", "go", "rust", "express", "django", "flask", "fastapi"],
    "DevOps": ["docker", "kubernetes", "aws", "azure", "gcp", "git"],
    "Algorithms": ["sorting", "searching", "dynamic programming", "greedy", "recursion", "backtracking"],
    "Data Structures": ["arrays", "linked lists", "trees", "graphs", "hash tables", "stacks", "queues"],
    "Code Quality": ["clean code", "testing", "refactoring", "design patterns", "code review"]
}

class TagMapper:
    """
    Service for mapping and managing tags in the system.
    Handles normalization, deduplication, and parent-child relationships.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.tag_repo = TagRepository(db)
        self.tag_normalizer = TagNormalizer(self.tag_repo)
    
    def normalize_tag_name(self, name: str) -> str:
        """
        Normalize a tag name to its standard form.
        
        Args:
            name: The tag name to normalize
            
        Returns:
            Normalized tag name
        """
        # Use the new comprehensive normalizer
        normalized_names = self.tag_normalizer.normalize_tag_names([name])
        if normalized_names:
            return normalized_names[0]
        return name
    
    def find_similar_tag(self, name: str, threshold: float = 0.9) -> Optional[Tag]:
        """
        Find a similar existing tag using fuzzy matching.
        
        Args:
            name: Tag name to search for
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            Similar tag or None if no similar tag found
        """
        # Try exact match (case insensitive) first
        exact_match = self.tag_repo.get_by_name_case_insensitive(name)
        if exact_match:
            return exact_match
        
        # Get all tags
        all_tags = self.db.query(Tag).all()
        
        # Normalized input name
        norm_name = self.normalize_tag_name(name)
        
        # Find the most similar tag
        most_similar = None
        highest_ratio = 0
        
        for tag in all_tags:
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, norm_name.lower(), tag.name.lower()).ratio()
            
            # If this is the most similar tag so far and above threshold
            if ratio > highest_ratio and ratio >= threshold:
                highest_ratio = ratio
                most_similar = tag
        
        return most_similar
    
    def get_or_create_parent_categories(self) -> Dict[str, Tag]:
        """
        Get or create the main tag categories.
        
        Returns:
            Dictionary mapping category names to Tag objects
        """
        categories = {}
        
        for category_name in TAG_CATEGORIES.keys():
            # Try to find existing category
            category_tag = self.db.query(Tag).filter(
                func.lower(Tag.name) == category_name.lower()
            ).first()
            
            if not category_tag:
                # Create new category
                logger.info(f"Creating new category: {category_name}")
                category_tag = Tag(
                    id=uuid.uuid4(),
                    name=category_name,
                    tag_type=TagType.category,
                    is_featured=True
                )
                self.db.add(category_tag)
                self.db.flush()
            
            categories[category_name] = category_tag
            
        return categories
    
    def find_suitable_parent_categories(self, tag_name: str) -> List[str]:
        """
        Find suitable parent categories for a tag based on its name.
        
        Args:
            tag_name: Name of the tag
            
        Returns:
            List of suitable parent category names
        """
        tag_lower = tag_name.lower()
        suitable_categories = []
        
        for category, related_tags in TAG_CATEGORIES.items():
            # Check if tag name matches any tag in this category
            if any(related.lower() in tag_lower or tag_lower in related.lower() for related in related_tags):
                suitable_categories.append(category)
        
        return suitable_categories
    
    def get_or_create_tag(self, name: str, description: str = None, parent_tag_id: uuid.UUID = None) -> Tag:
        """
        Get an existing tag or create a new one.
        
        Args:
            name: Tag name
            description: Optional description
            parent_tag_id: Optional parent tag ID
            
        Returns:
            Tag object
        """
        # Normalize name
        normalized_name = self.normalize_tag_name(name)
        
        # Try to find existing tag (case insensitive)
        existing_tag = self.tag_repo.get_by_name_case_insensitive(normalized_name)
        
        if existing_tag:
            logger.info(f"Found existing tag: {existing_tag.name}")
            return existing_tag
        
        # Try to find similar tag
        similar_tag = self.find_similar_tag(normalized_name)
        
        if similar_tag:
            logger.info(f"Found similar tag: {similar_tag.name} for {normalized_name}")
            return similar_tag
        
        # Create new tag
        logger.info(f"Creating new tag: {normalized_name}")
        
        # Determine tag type based on context
        tag_type = TagType.concept  # Default
        
        # For known technologies, use the technology type
        if name.lower() in TECH_NAME_MAPPINGS:
            tag_type = TagType.technology
        
        # Create tag
        new_tag = Tag(
            id=uuid.uuid4(),
            name=normalized_name,
            description=description,
            tag_type=tag_type,
            parent_tag_id=parent_tag_id
        )
        
        self.db.add(new_tag)
        self.db.flush()
        
        # If no parent provided, try to find suitable categories
        if not parent_tag_id:
            parent_categories = self.get_or_create_parent_categories()
            suitable_categories = self.find_suitable_parent_categories(normalized_name)
            
            # If suitable parent found, set as the main parent
            if suitable_categories:
                main_category = suitable_categories[0]
                new_tag.parent_tag_id = parent_categories[main_category].id
                
                # If more than one suitable category, create additional parent-child relationships
                # This would require a many-to-many relationship for parent-child, which might need schema changes
                # For now, we just log this information
                if len(suitable_categories) > 1:
                    logger.info(f"Tag {normalized_name} could also belong to: {', '.join(suitable_categories[1:])}")
        
        self.db.commit()
        return new_tag
    
    def map_tag_names_to_tags(self, tag_names: List[str]) -> List[Tag]:
        """
        Map a list of tag names to actual Tag objects, creating missing tags if needed.
        
        Args:
            tag_names: List of tag names
            
        Returns:
            List of Tag objects
        """
        tags = []
        
        # Ensure list has no duplicates
        tag_names = list(set(tag_name.strip() for tag_name in tag_names if tag_name and tag_name.strip()))
        
        logger.info(f"Mapping {len(tag_names)} tag names to tags")
        
        # First normalize all tag names
        normalized_names = self.tag_normalizer.normalize_tag_names(tag_names)
        
        # Then map to existing tags if possible
        mapped_names = self.tag_normalizer.map_to_existing_tags(normalized_names)
        
        logger.info(f"Original tags: {tag_names}")
        logger.info(f"Normalized tags: {normalized_names}")
        logger.info(f"Mapped to existing tags: {mapped_names}")
        
        for name in mapped_names:
            logger.info(f"Processing tag: {name}")
            tag = self.get_or_create_tag(name)
            if tag:
                tags.append(tag)
                
        return tags
    
    def merge_tag(self, source_tag_id, target_tag_id):
        """
        Merge one tag into another, preserving all relationships
        
        Args:
            source_tag_id: ID of the tag to merge (will be removed)
            target_tag_id: ID of the tag to keep and merge into
            
        Returns:
            The target tag with merged relationships
        """
        source_tag = self.db.query(Tag).filter(Tag.id == source_tag_id).first()
        target_tag = self.db.query(Tag).filter(Tag.id == target_tag_id).first()
        
        if not source_tag or not target_tag:
            raise ValueError(f"Source or target tag not found: {source_tag_id}, {target_tag_id}")
            
        logger.info(f"Merging tag '{source_tag.name}' ({source_tag_id}) into '{target_tag.name}' ({target_tag_id})")
        
        # Merge problems
        for problem in source_tag.problems:
            if problem not in target_tag.problems:
                target_tag.problems.append(problem)
        
        # Update child tags of source to point to target
        for child in source_tag.children:
            child.parent = target_tag
        
        # If source tag has a parent and target doesn't, keep that parent relationship
        if source_tag.parent and not target_tag.parent:
            target_tag.parent = source_tag.parent
        
        # Delete the source tag
        self.db.delete(source_tag)
        self.db.flush()
        
        return target_tag
        
    def merge_duplicate_tags(self) -> Dict[str, int]:
        """
        Find and merge duplicate tags in the system.
        
        Returns:
            Dictionary with statistics about the merge operation
        """
        # Stats to return
        stats = {
            "duplicate_sets": 0,
            "tags_merged": 0,
            "problem_associations_updated": 0
        }
        
        # Get all tags
        all_tags = self.db.query(Tag).all()
        
        # Group tags by lowercase name
        tags_by_lowercase = {}
        for tag in all_tags:
            key = tag.name.lower()
            if key not in tags_by_lowercase:
                tags_by_lowercase[key] = []
            tags_by_lowercase[key].append(tag)
        
        # Find duplicate sets
        duplicates = [tags for key, tags in tags_by_lowercase.items() if len(tags) > 1]
        stats["duplicate_sets"] = len(duplicates)
        
        for duplicate_set in duplicates:
            try:
                # Select primary tag (the one to keep)
                primary_tag = self._select_primary_tag(duplicate_set)
                
                # Ensure primary tag has normalized name
                primary_tag.name = self.normalize_tag_name(primary_tag.name)
                
                # Merge other tags into primary
                for tag in duplicate_set:
                    if tag.id == primary_tag.id:
                        continue
                    
                    # Use the merge_tag function
                    self.merge_tag(tag.id, primary_tag.id)
                    stats["tags_merged"] += 1
            except Exception as e:
                logger.error(f"Failed to merge duplicate tags: {str(e)}")
        
        # Commit changes
        self.db.commit()
        return stats
    
    def _select_primary_tag(self, tags: List[Tag]) -> Tag:
        """
        Select the primary tag from a list of duplicate tags.
        
        Args:
            tags: List of duplicate tags
            
        Returns:
            The primary tag to keep
        """
        if not tags:
            raise ValueError("Empty tag list")
        
        # First priority: tags with parent tags
        tags_with_parents = [t for t in tags if t.parent_tag_id]
        if tags_with_parents:
            tags = tags_with_parents
        
        # Second priority: properly capitalized names
        normalized_name = self.normalize_tag_name(tags[0].name)
        tags_with_proper_case = [t for t in tags if t.name == normalized_name]
        if tags_with_proper_case:
            tags = tags_with_proper_case
        
        # Third priority: tags with more problem associations
        tags.sort(key=lambda t: len(getattr(t, 'problems', [])), reverse=True)
        
        # Fourth priority: tags with descriptions
        tags_with_desc = [t for t in tags if t.description]
        if tags_with_desc:
            return tags_with_desc[0]
        
        return tags[0]

# Factory function
def get_tag_mapper(db: Session) -> TagMapper:
    """
    Factory function for TagMapper
    
    Args:
        db: Database session
        
    Returns:
        TagMapper instance
    """
    return TagMapper(db)
