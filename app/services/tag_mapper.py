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
    
    def __init__(self, db: Session = None):
        self.db = db
        self.tag_repo = TagRepository(db) if db else None
        self.tag_normalizer = TagNormalizer(self.tag_repo) if db else None
    
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
        Uses case-insensitive lookup to prevent duplication.
        
        Returns:
            Dictionary mapping category names to Tag objects
        """
        categories = {}
        
        for category_name in TAG_CATEGORIES.keys():
            try:
                # IMPORTANT: First look for existing tag with case-insensitive safe method
                existing_category = self.tag_repo.get_by_name_case_insensitive_safe(category_name)
                
                if existing_category:
                    # Found an existing category, use it
                    logger.info(f"Found existing category: {existing_category.name} (ID: {existing_category.id})")
                    category_tag = existing_category
                else:
                    # Use the safe case-insensitive method to create the category
                    logger.info(f"Creating new category safely: {category_name}")
                    category_tag = self.tag_repo.get_or_create_case_insensitive(category_name)
                    
                    # Set additional properties for newly created category tags
                    category_tag.tag_type = TagType.category
                    category_tag.is_featured = True
                    self.db.flush()
            except Exception as e:
                logger.error(f"Error handling category tag '{category_name}': {str(e)}")
                # Try one more direct approach as fallback if there's an error
                category_tag = self.db.query(Tag).filter(func.lower(Tag.name) == category_name.lower()).first()
                if not category_tag:
                    logger.warning(f"Could not create category tag for '{category_name}', skipping")
                    continue
            
            # Store both the original name and the actual name for consistent lookups
            categories[category_name] = category_tag
            if category_name.lower() != category_tag.name.lower():
                categories[category_tag.name] = category_tag
            
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
    
    def get_or_create_tag(self, name: str, description: str = None, parent_tag_id: uuid.UUID = None, **kwargs) -> Tag:
        """
        Get an existing tag or create a new one using case-insensitive lookup.
        
        Args:
            name: Tag name
            description: Optional description
            parent_tag_id: Optional parent tag ID (for backward compatibility)
            **kwargs: Additional tag attributes
            
        Returns:
            Tag object
        """
        # Normalize name
        normalized_name = self.normalize_tag_name(name)
        
        try:
            # IMPORTANT: First use the case-insensitive lookup to find existing tag
            existing_tag = self.tag_repo.get_by_name_case_insensitive_safe(normalized_name)
            
            if existing_tag:
                logger.info(f"Found existing tag: {existing_tag.name} (ID: {existing_tag.id})")
                
                # If parent_tag_id is specified and it's not already a parent of this tag,
                # add the parent-child relationship
                if parent_tag_id:
                    existing_parents = self.tag_repo.get_parent_tags(existing_tag.id)
                    existing_parent_ids = [p.id for p in existing_parents]
                    
                    if parent_tag_id not in existing_parent_ids:
                        try:
                            self.tag_repo.add_parent_child_relationship(parent_tag_id, existing_tag.id)
                            logger.info(f"Added parent relationship for existing tag: {existing_tag.name}")
                        except ValueError as e:
                            logger.warning(f"Failed to add parent relationship: {str(e)}")
                    
                return existing_tag
            
            # Use the safe case-insensitive method to get or create the tag
            # This avoids the unique constraint violation by handling the lookup and creation atomically
            logger.info(f"Creating new tag with case-insensitive method: {normalized_name}")
            new_tag = self.tag_repo.get_or_create_case_insensitive(normalized_name)
            
            # Set additional properties for the tag
            # Determine tag type based on context
            tag_type = kwargs.get('tag_type', TagType.concept)  # Default
            
            # For known technologies, use the technology type
            if normalized_name.lower() in TECH_NAME_MAPPINGS:
                tag_type = TagType.technology
            
            # Update tag details
            if description is not None:
                new_tag.description = description
                
            new_tag.tag_type = tag_type
            new_tag.is_featured = kwargs.get('is_featured', False)
            new_tag.is_private = kwargs.get('is_private', False)
            
            # Flush to ensure the tag is saved before we add relationships
            # Do not commit here to let the calling context manage its own transactions
            self.db.flush()
            
            # Now handle parent relationships with the new multi-parent model
            # First for backward compatibility with parent_tag_id
            if parent_tag_id:
                try:
                    self.tag_repo.add_parent_child_relationship(parent_tag_id, new_tag.id)
                    logger.info(f"Added parent relationship for new tag: {new_tag.name}")
                except ValueError as e:
                    logger.warning(f"Failed to add parent relationship: {str(e)}")
            else:
                # Try to find suitable categories if no parent provided
                parent_categories = self.get_or_create_parent_categories()
                suitable_categories = self.find_suitable_parent_categories(normalized_name)
                
                # Add parent relationships for suitable categories
                if suitable_categories:
                    for category_name in suitable_categories:
                        try:
                            category_tag = parent_categories.get(category_name)
                            if category_tag:
                                self.tag_repo.add_parent_child_relationship(category_tag.id, new_tag.id)
                                logger.info(f"Added category parent relationship: {category_name} -> {new_tag.name}")
                        except ValueError as e:
                            logger.warning(f"Failed to add category relationship: {str(e)}")
            
            return new_tag
                
        except Exception as e:
            logger.error(f"Error in get_or_create_tag for '{normalized_name}': {str(e)}")
            # Fallback to traditional method as a last resort
            existing_tag = self.db.query(Tag).filter(func.lower(Tag.name) == normalized_name.lower()).first()
            if existing_tag:
                return existing_tag
            else:
                logger.warning(f"Failed to create or find tag for '{normalized_name}', returning None")
                return None
    
    def map_tag_names_to_tags(self, tag_names: List[str]) -> List[Tag]:
        """
        Map a list of tag names to actual Tag objects, creating missing tags if needed.
        
        Args:
            tag_names: List of tag names
            
        Returns:
            List of Tag objects
        """
        if not self.db:
            logger.warning("Cannot map tags without database session")
            return []
            
        # First, normalize all the tag names
        normalized_names = self.tag_normalizer.normalize_tag_names(tag_names)
        
        # Check for existing tags and create new ones as needed
        tags = []
        for name in normalized_names:
            if not name.strip():
                continue
            tag = self.get_or_create_tag(name)
            if tag:
                tags.append(tag)
                
        # Deduplicate (in case we somehow ended up with duplicate tag objects)
        unique_tags = []
        tag_ids_seen = set()
        for tag in tags:
            if tag.id not in tag_ids_seen:
                unique_tags.append(tag)
                tag_ids_seen.add(tag.id)
                
        return unique_tags
        
    def map_tag_names_to_tag_ids(self, tag_names: List[str]) -> List[uuid.UUID]:
        """
        Map a list of tag names to their tag IDs, creating missing tags if needed.
        This method avoids session binding issues by returning UUIDs instead of Tag objects.
        
        Args:
            tag_names: List of tag names
            
        Returns:
            List of tag UUIDs (IDs)
        """
        if not self.db:
            logger.warning("Cannot map tags without database session")
            return []
            
        # First, normalize all the tag names
        normalized_names = self.tag_normalizer.normalize_tag_names(tag_names)
        
        # Check for existing tags and create new ones as needed, but only collect IDs
        tag_ids = []
        for name in normalized_names:
            if not name.strip():
                continue
            tag = self.get_or_create_tag(name)
            if tag and tag.id:
                tag_ids.append(tag.id)
                
        # Deduplicate
        unique_tag_ids = list(set(tag_ids))
        logger.info(f"Mapped {len(tag_names)} tag names to {len(unique_tag_ids)} unique tag IDs")
                
        return unique_tag_ids
    
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
        
        # First priority: tags with parent tags (now using the hierarchy relationship)
        tags_with_parents = []
        for tag in tags:
            # Check if tag has parents using the new hierarchy system
            parents = self.tag_repo.get_parent_tags(tag.id)
            if parents and len(parents) > 0:
                tags_with_parents.append(tag)
                
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

    def get_additional_parents(self, tag_name: str) -> List[str]:
        """
        Get additional parent categories for a tag based on its name.
        This supports multi-parent relationships in the tag hierarchy.
        
        Args:
            tag_name: The name of the tag to find additional parents for
            
        Returns:
            List of parent category names that this tag should belong to
        """
        # Normalize the tag name for consistent lookup
        tag_name_lower = tag_name.lower()
        
        # Initialize empty list of parent categories
        additional_parents = []
        
        # Look through all category definitions to find which ones this tag should belong to
        for category, tags in TAG_CATEGORIES.items():
            if tag_name_lower in [t.lower() for t in tags]:
                # This tag belongs in this category
                additional_parents.append(category)
        
        # Special case handling for common multi-category technologies
        if tag_name_lower in ["typescript", "javascript"]:
            additional_parents.extend(["Languages", "Frontend"])
        elif tag_name_lower in ["python", "java"]:
            additional_parents.extend(["Languages", "Backend"])
        elif tag_name_lower == "node.js" or tag_name_lower == "nodejs":
            additional_parents.extend(["Frameworks", "Backend"])
        elif tag_name_lower in ["react", "angular", "vue", "vue.js"]:
            additional_parents.extend(["Frameworks", "Frontend"])
        elif tag_name_lower in ["django", "flask", "fastapi", "express"]:
            additional_parents.extend(["Frameworks", "Backend"])
            
        # Remove duplicates while preserving order
        unique_parents = []
        for parent in additional_parents:
            if parent not in unique_parents:
                unique_parents.append(parent)
                
        return unique_parents

# Factory function
def get_tag_mapper(db: Session = None) -> TagMapper:
    """
    Factory function for TagMapper
    
    Args:
        db: Optional database session. If not provided, a limited functionality
            instance will be returned (useful for using static methods)
        
    Returns:
        TagMapper instance
    """
    return TagMapper(db)
