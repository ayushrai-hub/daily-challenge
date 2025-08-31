"""
Base interface for AI provider adapters.
Defines the common contract that all AI model implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class AIPlatformError(Exception):
    """Exception raised for errors in the AI platform API calls."""
    pass


class BaseAIProvider(ABC):
    """Base abstract class for AI provider implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the AI provider with necessary setup."""
        pass
    
    @abstractmethod
    async def generate_problems(self, 
                               source_data: Dict[str, Any], 
                               num_problems: int = 3,
                               temperature: float = 0.7) -> List[Dict[str, Any]]:
        """
        Generate coding problems based on source data.
        
        Args:
            source_data: Dictionary containing data from content sources
            num_problems: Number of problems to generate
            temperature: Controls randomness in generation (0.0 to 1.0)
            
        Returns:
            List of generated problem dictionaries with title, description, difficulty,
            solution, and tags
        """
        pass
    
    @abstractmethod
    async def validate_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a generated problem for quality and completeness.
        
        Args:
            problem: Problem dictionary to validate
            
        Returns:
            Dictionary with validation results and improved problem
        """
        pass
    
    @abstractmethod
    async def generate_test_cases(self, problem: Dict[str, Any], 
                                num_test_cases: int = 5) -> List[Dict[str, Any]]:
        """
        Generate test cases for a problem.
        
        Args:
            problem: Problem dictionary
            num_test_cases: Number of test cases to generate
            
        Returns:
            List of test case dictionaries with inputs and expected outputs
        """
        pass
