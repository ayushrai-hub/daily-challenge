from typing import Any, Dict, Optional
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)

async def make_request(
    url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Make an HTTP request using httpx.
    
    Args:
        url: The URL to request
        method: HTTP method (GET, POST, etc.)
        params: Query parameters
        data: Request body data
        headers: HTTP headers
        timeout: Request timeout in seconds
        
    Returns:
        Response data as dictionary
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method == "GET":
                response = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await client.post(url, json=data, params=params, headers=headers)
            elif method == "PUT":
                response = await client.put(url, json=data, params=params, headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {str(e)}")
            raise