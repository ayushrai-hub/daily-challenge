"""
Base interface for content source connectors.
Defines the common contract that all platform implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class ContentSourceError(Exception):
    """Exception raised for errors in content source API calls."""
    pass


class BaseContentSource(ABC):
    """Base abstract class for content source implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the content source connector with necessary setup."""
        pass
    
    @abstractmethod
    async def fetch_content(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch content from the source platform.
        
        Args:
            query_params: Dictionary of parameters to control content fetching
            
        Returns:
            Dictionary containing the raw fetched content
        """
        pass
    
    @abstractmethod
    async def process_content(self, raw_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw content into a normalized format.
        
        Args:
            raw_content: Raw content from the fetch_content method
            
        Returns:
            Processed content in a standardized format
        """
        pass
