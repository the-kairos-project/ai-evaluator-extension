"""
Base provider class for LLM API calls.

This module defines the base interface and common functionality for all LLM providers.
"""

from abc import ABC, abstractmethod
import logging
import time
from typing import Dict, Any, List, Optional

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel


# Set up logging
logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Message model for chat completion."""
    
    role: str
    content: str


class ProviderRequest(BaseModel):
    """Base model for provider API requests."""
    
    api_key: str
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 500
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class ProviderResponse(BaseModel):
    """Base model for provider API responses."""
    
    content: str
    provider: str
    model: str
    raw_response: Dict[str, Any]


class BaseProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, timeout: float = 30.0):
        """Initialize the provider.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.name = self.__class__.__name__.lower().replace('provider', '')
        logger.info(f"Initialized {self.name} provider")
    
    @abstractmethod
    async def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        """Prepare the request payload for the provider API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            Dict[str, Any]: Prepared request payload
        """
        pass
    
    @abstractmethod
    async def prepare_headers(self, request: ProviderRequest) -> Dict[str, str]:
        """Prepare the request headers for the provider API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            Dict[str, str]: Prepared request headers
        """
        pass
    
    @abstractmethod
    async def get_api_url(self) -> str:
        """Get the API URL for the provider.
        
        Returns:
            str: API URL
        """
        pass
    
    @abstractmethod
    async def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from the provider API response.
        
        Args:
            response: Provider API response
            
        Returns:
            str: Extracted content
        """
        pass
    
    async def generate(self, payload: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
        """Generate a completion using the provider API.
        
        Args:
            payload: Request payload
            api_key: Optional API key to override the default
            
        Returns:
            Dict[str, Any]: Provider API response
            
        Raises:
            HTTPException: If the request fails
        """
        # Optional normalization: some providers (e.g., Anthropic) expect a
        # top-level `system` parameter rather than a message with role "system".
        # Allow per-call override with payload["normalize_system_top_level"].
        normalize_flag = payload.get("normalize_system_top_level")
        if normalize_flag is None:
            # Default: enable normalization for Anthropic only
            normalize_flag = self.name == "anthropic"

        if normalize_flag:
            raw_msgs = payload.get("messages", []) or []
            system_parts = [m.get("content") for m in raw_msgs if str(m.get("role", "")).lower() == "system"]
            user_msgs = [m for m in raw_msgs if str(m.get("role", "")).lower() != "system"]
            if system_parts:
                payload["system"] = "\n".join(system_parts)
            payload["messages"] = user_msgs

        # Create a ProviderRequest from the (possibly normalized) payload
        request = ProviderRequest(
            api_key=api_key or payload.get("api_key", ""),
            model=payload.get("model", ""),
            messages=[Message(role=m.get("role"), content=m.get("content"))
                      for m in payload.get("messages", [])],
            max_tokens=payload.get("max_tokens"),
            temperature=payload.get("temperature"),
            top_p=payload.get("top_p")
        )
        
        # Call the provider API
        response = await self.call(request)
        
        # Return the raw response
        return response.raw_response
    
    async def call(self, request: ProviderRequest) -> ProviderResponse:
        """Call the provider API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            ProviderResponse: Provider API response
            
        Raises:
            HTTPException: If the request fails
        """
        try:
            payload = await self.prepare_request(request)
            headers = await self.prepare_headers(request)
            api_url = await self.get_api_url()
            
            logger.info(f"Calling {self.name} API with model {request.model}")
            logger.debug(f"API URL: {api_url}")
            logger.debug(f"Request payload: {payload}")
            
            # Mask API key in logs
            masked_headers = headers.copy()
            if "Authorization" in masked_headers:
                masked_headers["Authorization"] = "Bearer sk-...MASKED..."
            if "x-api-key" in masked_headers:
                masked_headers["x-api-key"] = "sk-...MASKED..."
            logger.debug(f"Request headers: {masked_headers}")
            
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers=headers,
                )
                
                # Check for errors
                response.raise_for_status()
                
                # Parse response
                response_data = response.json()
                
                # Calculate request duration
                duration = time.time() - start_time
                logger.info(f"{self.name} API call completed in {duration:.2f}s")
                
                # Extract content
                content = await self.extract_content(response_data)
                logger.debug(f"Response content length: {len(content)} chars")
                
                return ProviderResponse(
                    content=content,
                    provider=self.name,
                    model=request.model,
                    raw_response=response_data
                )
                
        except httpx.HTTPStatusError as e:
            # Forward provider error response
            status_code = e.response.status_code
            error_info = {}
            
            try:
                if e.response.headers.get("content-type") == "application/json":
                    error_info = e.response.json()
                else:
                    error_info = {"error": str(e)}
            except Exception as json_error:
                error_info = {"error": str(e), "parse_error": str(json_error)}
            
            logger.error(f"{self.name} API error: {status_code} - {error_info}")
            
            # Customize error message based on status code
            if status_code == 401:
                detail = f"{self.name.capitalize()} API authentication error. Please check your API key."
            elif status_code == 429:
                detail = f"{self.name.capitalize()} API rate limit exceeded. Please try again later."
            elif status_code >= 500:
                detail = f"{self.name.capitalize()} API server error. Please try again later."
            else:
                detail = f"{self.name.capitalize()} API error: {error_info}"
            
            raise HTTPException(
                status_code=status_code,
                detail=detail
            )
        except httpx.TimeoutException as e:
            # Timeout errors
            logger.error(f"{self.name} API timeout: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"{self.name.capitalize()} API request timed out after {self.timeout}s. Please try again later."
            )
        except httpx.RequestError as e:
            # Network-related errors
            logger.error(f"Error communicating with {self.name} API: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error communicating with {self.name.capitalize()} API: {str(e)}"
            )
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error with {self.name} API: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error with {self.name.capitalize()} API: {str(e)}"
            ) 