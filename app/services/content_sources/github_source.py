"""
GitHub content source implementation.
Fetches code, issues, and discussions from GitHub repositories.
"""
import httpx
import base64
from typing import Dict, List, Any, Optional, Union
from app.core.config import settings
from app.core.logging import get_logger
from app.services.content_sources.base import BaseContentSource, ContentSourceError

logger = get_logger()


class GitHubSource(BaseContentSource):
    """GitHub content source implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the GitHub source connector.
        
        Args:
            api_key: GitHub API key (defaults to settings)
        """
        self.api_key = api_key or settings.GITHUB_API_KEY
        self.base_url = "https://api.github.com"
        self.client = None
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the GitHub API client."""
        if self.is_initialized:
            return
            
        try:
            # Initialize httpx client for API calls
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"token {self.api_key}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "DailyChallengeApp"
                }
            )
            self.is_initialized = True
            logger.info("GitHub content source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub source: {str(e)}")
            raise ContentSourceError(f"GitHub initialization failed: {str(e)}")
    
    async def fetch_content(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch content from GitHub based on query parameters.
        
        Args:
            query_params: Dictionary with parameters such as:
                - repo: Repository name (e.g., "username/repo")
                - content_type: Type of content to fetch (code, issues, discussions)
                - topic: Optional topic filter
                - language: Optional language filter
                - max_items: Maximum number of items to fetch (default 10)
                
        Returns:
            Dictionary with raw content from GitHub
        """
        if not self.is_initialized:
            await self.initialize()
            
        repo = query_params.get("repo")
        content_type = query_params.get("content_type", "code")
        max_items = query_params.get("max_items", 10)
        
        if not repo:
            raise ContentSourceError("Repository name is required")
            
        results = {
            "repo": repo,
            "content_type": content_type,
            "items": []
        }
        
        try:
            if content_type == "code":
                # Get repository contents from root
                await self._fetch_code_content(repo, results, max_items)
            
            elif content_type == "issues":
                # Get issues from repository
                state = query_params.get("state", "all")
                labels = query_params.get("labels")
                
                params = {
                    "state": state,
                    "per_page": max_items,
                    "sort": "updated",
                    "direction": "desc"
                }
                
                if labels:
                    params["labels"] = labels
                
                response = await self.client.get(
                    f"{self.base_url}/repos/{repo}/issues",
                    params=params
                )
                response.raise_for_status()
                
                issues = response.json()
                # Filter out pull requests which are also returned by the issues endpoint
                issues = [issue for issue in issues if "pull_request" not in issue]
                
                for issue in issues[:max_items]:
                    results["items"].append({
                        "type": "issue",
                        "id": issue["id"],
                        "number": issue["number"],
                        "title": issue["title"],
                        "body": issue["body"] or "",
                        "state": issue["state"],
                        "labels": [label["name"] for label in issue.get("labels", [])],
                        "created_at": issue["created_at"],
                        "updated_at": issue["updated_at"],
                        "url": issue["html_url"]
                    })
            
            elif content_type == "discussions":
                # Note: This requires GraphQL API for GitHub Discussions
                # For simplicity, we'll use a simpler approach here
                logger.warning("GitHub Discussions fetching not fully implemented - using issues instead")
                # Redirect to issues as a fallback
                query_params["content_type"] = "issues"
                return await self.fetch_content(query_params)
                
            else:
                raise ContentSourceError(f"Unsupported content type: {content_type}")
                
            logger.info(f"Successfully fetched {len(results['items'])} {content_type} items from GitHub repo: {repo}")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise ContentSourceError(f"GitHub API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch GitHub content: {str(e)}")
            raise ContentSourceError(f"GitHub content fetch failed: {str(e)}")
    
    async def _fetch_code_content(self, repo: str, results: Dict[str, Any], max_items: int, path: str = ""):
        """Helper to fetch code content, with recursive directory traversal."""
        try:
            response = await self.client.get(f"{self.base_url}/repos/{repo}/contents/{path}")
            response.raise_for_status()
            
            contents = response.json()
            
            if not isinstance(contents, list):
                # Single file
                contents = [contents]
                
            files_fetched = 0
            
            for item in contents:
                if files_fetched >= max_items:
                    break
                    
                if item["type"] == "file":
                    # Check if it's a code file we're interested in
                    if self._is_code_file(item["name"]):
                        # Fetch file content
                        if "content" not in item:
                            file_response = await self.client.get(item["url"])
                            file_response.raise_for_status()
                            item = file_response.json()
                            
                        try:
                            content = base64.b64decode(item["content"]).decode("utf-8")
                        except Exception:
                            content = "Unable to decode content"
                            
                        results["items"].append({
                            "type": "file",
                            "name": item["name"],
                            "path": item["path"],
                            "content": content,
                            "size": item["size"],
                            "url": item["html_url"]
                        })
                        files_fetched += 1
                        
                elif item["type"] == "dir" and files_fetched < max_items:
                    # Recursively fetch directory contents, but be careful with depth
                    if path.count("/") < 2:  # Limit directory depth to avoid too many API calls
                        dir_path = item["path"]
                        await self._fetch_code_content(repo, results, max_items - files_fetched, dir_path)
                        files_fetched = len([i for i in results["items"] if i["type"] == "file"])
        
        except httpx.HTTPStatusError as e:
            logger.warning(f"Error fetching GitHub content at {path}: {e.response.status_code}")
        except Exception as e:
            logger.warning(f"Error processing GitHub content at {path}: {str(e)}")
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if the file is a code file we're interested in."""
        code_extensions = [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cs", 
            ".go", ".rb", ".php", ".scala", ".kt", ".rs", ".swift"
        ]
        return any(filename.endswith(ext) for ext in code_extensions)
    
    async def process_content(self, raw_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw GitHub content into a normalized format.
        
        Args:
            raw_content: Raw content from the fetch_content method
            
        Returns:
            Processed content with extracted code and metadata
        """
        content_type = raw_content.get("content_type", "")
        items = raw_content.get("items", [])
        repo = raw_content.get("repo", "")
        
        processed_result = {
            "source": "github",
            "repo": repo,
            "content_type": content_type,
            "extracted_content": "",
            "metadata": {
                "item_count": len(items),
                "content_summary": f"GitHub {content_type} from {repo}"
            }
        }
        
        extracted_text = []
        
        for item in items:
            if content_type == "code" and item.get("type") == "file":
                extracted_text.append(f"--- FILE: {item['path']} ---\n{item['content']}\n\n")
            
            elif content_type == "issues" and item.get("type") == "issue":
                extracted_text.append(
                    f"--- ISSUE #{item['number']}: {item['title']} ---\n"
                    f"State: {item['state']}\n"
                    f"Labels: {', '.join(item['labels'])}\n\n"
                    f"{item['body']}\n\n"
                )
        
        processed_result["extracted_content"] = "\n".join(extracted_text)
        
        logger.info(f"Processed {len(items)} items from GitHub repo: {repo}")
        return processed_result
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
