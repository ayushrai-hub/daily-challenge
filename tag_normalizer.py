"""
Tag normalization service to ensure consistent tag naming and proper capitalization.
This helps prevent duplicate tags with different cases (e.g., "typescript" vs "TypeScript").
"""
from typing import Dict, List, Optional, Set
import re
from app.core.logging import get_logger
from app.repositories.tag import TagRepository

logger = get_logger()

class TagNormalizer:
    """Service to normalize tag names for consistency."""
    
    # Known technology names with their proper capitalization
    # This dictionary will ensure proper capitalization for common technologies
    KNOWN_TECHNOLOGIES = {
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "python": "Python",
        "java": "Java",
        "csharp": "C#",
        "c#": "C#",
        "cplusplus": "C++",
        "c++": "C++",
        "golang": "Go",
        "react": "React",
        "reactjs": "React",
        "vuejs": "Vue.js",
        "vue": "Vue.js",
        "angular": "Angular",
        "angularjs": "AngularJS",
        "nodejs": "Node.js",
        "node.js": "Node.js",
        "node": "Node.js",
        "nextjs": "Next.js",
        "next.js": "Next.js",
        "nestjs": "NestJS",
        "expressjs": "Express.js",
        "express": "Express.js",
        "mongodb": "MongoDB",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "redis": "Redis",
        "graphql": "GraphQL",
        "restapi": "REST API",
        "rest": "REST API",
        "api": "API",
        "http": "HTTP",
        "html": "HTML",
        "css": "CSS",
        "sass": "Sass",
        "scss": "SCSS",
        "jquery": "jQuery",
        "eslint": "ESLint",
        "tslint": "TSLint",
        "webpack": "Webpack",
        "babel": "Babel",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "k8s": "Kubernetes",
        "aws": "AWS",
        "azure": "Azure",
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "pytest": "pytest",  # Note: pytest is officially lowercase
        "numpy": "NumPy",
        "pandas": "pandas",  # Note: pandas is officially lowercase
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "algorithms": "Algorithms",
        "datastructures": "Data Structures",
        "data structures": "Data Structures",
        "arrays": "Arrays",
        "linkedlists": "Linked Lists",
        "linked lists": "Linked Lists",
        "trees": "Trees",
        "graphs": "Graphs",
        "stacks": "Stacks",
        "queues": "Queues",
        "recursion": "Recursion",
        "sorting": "Sorting",
        "searching": "Searching",
        "dynamicprogramming": "Dynamic Programming",
        "dynamic programming": "Dynamic Programming",
        "ast": "AST",
        "compiler": "Compiler",
        "interpreter": "Interpreter",
    }
    
    # Common words that should not be capitalized in titles 
    # unless they are the first word
    LOWERCASE_WORDS = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 
                       'on', 'at', 'to', 'from', 'by', 'with', 'in', 'of'}
    
    def __init__(self, tag_repository: TagRepository):
        self.tag_repository = tag_repository
    
    def normalize_tag_names(self, tag_names: List[str]) -> List[str]:
        """
        Normalize a list of tag names to use consistent capitalization and naming.
        
        Args:
            tag_names: List of raw tag names to normalize
            
        Returns:
            List of normalized tag names
        """
        normalized_names = []
        
        for name in tag_names:
            if not name or not name.strip():
                continue
                
            # Clean the tag name (remove extra spaces, etc.)
            clean_name = self._clean_tag_name(name)
            
            # Try to find the canonical form in known technologies
            normalized_name = self._normalize_known_technology(clean_name)
            
            # If not found in known technologies, apply title case with special handling
            if normalized_name == clean_name.lower():
                normalized_name = self._apply_title_case(clean_name)
            
            # Log the normalization if it changed
            if normalized_name != name:
                logger.info(f"Normalized tag from '{name}' to '{normalized_name}'")
                
            normalized_names.append(normalized_name)
            
        return normalized_names
    
    def map_to_existing_tags(self, tag_names: List[str]) -> List[str]:
        """
        Map normalized tag names to existing tags in the database.
        
        Args:
            tag_names: List of normalized tag names
            
        Returns:
            List of tag names that may have been mapped to existing tags
        """
        mapped_names = []
        
        for name in tag_names:
            # Try to find exact match first
            existing_tag = self.tag_repository.get_by_name(name)
            
            if existing_tag:
                # Use the existing tag's exact name
                mapped_names.append(existing_tag.name)
                continue
                
            # Try to find case-insensitive match
            existing_tag = self.tag_repository.get_by_name_case_insensitive(name)
            
            if existing_tag:
                logger.info(f"Mapped tag '{name}' to existing tag '{existing_tag.name}'")
                mapped_names.append(existing_tag.name)
            else:
                # No match found, use the normalized name
                mapped_names.append(name)
                
        return mapped_names
    
    def _clean_tag_name(self, name: str) -> str:
        """Clean a tag name by removing extra spaces and special characters."""
        # Remove leading/trailing whitespace
        name = name.strip()
        
        # Replace multiple spaces with a single space
        name = re.sub(r'\s+', ' ', name)
        
        return name
    
    def _normalize_known_technology(self, name: str) -> str:
        """
        Normalize a tag name if it's a known technology.
        
        Args:
            name: The tag name to normalize
            
        Returns:
            Normalized tag name if it's a known technology, otherwise the lowercase name
        """
        # Remove any special characters for comparison
        cleaned_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
        
        # Check if it's a known technology
        if cleaned_name in self.KNOWN_TECHNOLOGIES:
            return self.KNOWN_TECHNOLOGIES[cleaned_name]
            
        # Also check direct match without cleaning
        if name.lower() in self.KNOWN_TECHNOLOGIES:
            return self.KNOWN_TECHNOLOGIES[name.lower()]
            
        return name.lower()
    
    def _apply_title_case(self, name: str) -> str:
        """
        Apply title case to a tag name, with special handling for common words.
        
        Args:
            name: The tag name to convert to title case
            
        Returns:
            The tag name in title case
        """
        words = name.lower().split()
        
        # If it's a single word, capitalize the first letter
        if len(words) == 1:
            return words[0].capitalize()
            
        # For multiple words, apply title case with special handling
        result = []
        for i, word in enumerate(words):
            if i == 0 or word not in self.LOWERCASE_WORDS:
                result.append(word.capitalize())
            else:
                result.append(word)
                
        return ' '.join(result)
