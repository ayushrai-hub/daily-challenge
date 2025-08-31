"""
Celery tasks for fetching content from various sources.
"""
import asyncio
from typing import Dict, List, Any, Optional
from celery import shared_task
from app.core.logging import get_logger
from app.services.content_sources.github_source import GitHubSource
from app.services.content_sources.stackoverflow_source import StackOverflowSource

logger = get_logger()


@shared_task(name="fetch_github_content", queue="content")
def fetch_github_content(
    api_key: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fetch content from GitHub based on query parameters.
    
    Args:
        api_key: GitHub API key (optional, will use settings if not provided)
        query_params: Parameters for content fetching:
            - repo: Repository name (e.g., "username/repo")
            - content_type: Type of content to fetch (code, issues, discussions)
            - topic: Optional topic filter
            - language: Optional language filter
            - max_items: Maximum number of items to fetch (default 10)
            
    Returns:
        Dictionary with processed content from GitHub
    """
    logger.info(f"Fetching GitHub content with params: {query_params}")
    
    if not query_params:
        query_params = {
            "repo": "microsoft/vscode", 
            "content_type": "code",
            "max_items": 5
        }
        logger.warning("No query params provided, using defaults")
    
    # Run async code in sync context
    async def _fetch_and_process():
        try:
            async with GitHubSource(api_key=api_key) as github_source:
                raw_content = await github_source.fetch_content(query_params)
                processed_content = await github_source.process_content(raw_content)
                return processed_content
        except Exception as e:
            logger.error(f"Error fetching GitHub content: {str(e)}")
            return {
                "source": "github",
                "error": str(e),
                "extracted_content": "",
                "metadata": {
                    "success": False,
                    "error_message": str(e)
                }
            }
    
    # Execute the async function
    return asyncio.run(_fetch_and_process())


@shared_task(name="fetch_stackoverflow_content", queue="content")
def fetch_stackoverflow_content(
    app_key: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fetch content from Stack Overflow based on query parameters.
    
    Args:
        app_key: Stack Overflow App Key from Stack Apps (optional, will use settings if not provided)
        query_params: Parameters for content fetching:
            - tags: List of tags to filter by
            - q: Search query
            - content_type: Type of content to fetch (questions, answers)
            - sort: Sort order (activity, votes, creation, relevance)
            - max_items: Maximum number of items to fetch (default 10)
            
    Returns:
        Dictionary with processed content from Stack Overflow
    """
    logger.info(f"Fetching Stack Overflow content with params: {query_params}")
    
    if not query_params:
        query_params = {
            "tags": ["python", "fastapi"],
            "content_type": "questions",
            "sort": "votes",
            "max_items": 5
        }
        logger.warning("No query params provided, using defaults")
    
    # Run async code in sync context
    async def _fetch_and_process():
        try:
            async with StackOverflowSource(app_key=app_key) as so_source:
                raw_content = await so_source.fetch_content(query_params)
                processed_content = await so_source.process_content(raw_content)
                return processed_content
        except Exception as e:
            logger.error(f"Error fetching Stack Overflow content: {str(e)}")
            return {
                "source": "stackoverflow",
                "error": str(e),
                "extracted_content": "",
                "metadata": {
                    "success": False,
                    "error_message": str(e)
                }
            }
    
    # Execute the async function
    return asyncio.run(_fetch_and_process())


@shared_task(name="fetch_combined_content", queue="content")
def fetch_combined_content(
    github_params: Optional[Dict[str, Any]] = None,
    stackoverflow_params: Optional[Dict[str, Any]] = None,
    github_api_key: Optional[str] = None,
    stackoverflow_app_key: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch content from multiple sources and combine the results.
    
    Args:
        github_params: GitHub query parameters
        stackoverflow_params: Stack Overflow query parameters
        github_api_key: GitHub API key
        stackoverflow_app_key: Stack Overflow App Key
        
    Returns:
        Dictionary with content from each source
    """
    combined_results = {}
    
    # Fetch GitHub content if parameters provided - using direct function calls instead of task.get()
    if github_params:
        try:
            # Direct function call instead of using apply_async().get()
            github_result = _fetch_github_content_sync(github_api_key, github_params)
            combined_results["github"] = github_result
        except Exception as e:
            logger.error(f"Error fetching GitHub content: {str(e)}")
            combined_results["github"] = {
                "error": f"Failed to fetch GitHub content: {str(e)}",
                "extracted_content": ""
            }
    
    # Fetch Stack Overflow content if parameters provided
    if stackoverflow_params:
        try:
            # Direct function call instead of using apply_async().get()
            stackoverflow_result = _fetch_stackoverflow_content_sync(stackoverflow_app_key, stackoverflow_params)
            combined_results["stackoverflow"] = stackoverflow_result
        except Exception as e:
            logger.error(f"Error fetching Stack Overflow content: {str(e)}")
            combined_results["stackoverflow"] = {
                "error": f"Failed to fetch Stack Overflow content: {str(e)}",
                "extracted_content": ""
            }
    
    return combined_results


def _fetch_github_content_sync(api_key: Optional[str], query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous version of fetch_github_content to avoid calling task.get() within a task"""
    return fetch_github_content(api_key=api_key, query_params=query_params)


def _fetch_stackoverflow_content_sync(app_key: Optional[str], query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous version of fetch_stackoverflow_content to avoid calling task.get() within a task"""
    return fetch_stackoverflow_content(app_key=app_key, query_params=query_params)
