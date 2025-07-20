"""
OpenAI provider implementation.
"""

from typing import Dict, Any

from .base import BaseProvider, ProviderRequest


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""
    
    async def get_api_url(self) -> str:
        """Get the API URL for OpenAI.
        
        Returns:
            str: OpenAI API URL
        """
        return "https://api.openai.com/v1/chat/completions"
    
    async def prepare_headers(self, request: ProviderRequest) -> Dict[str, str]:
        """Prepare the request headers for OpenAI API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            Dict[str, str]: Prepared request headers
        """
        return {
            "Authorization": f"Bearer {request.api_key}",
            "Content-Type": "application/json",
        }
    
    async def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        """Prepare the request payload for OpenAI API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            Dict[str, Any]: Prepared request payload
        """
        payload = {
            "model": request.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "max_tokens": request.max_tokens,
        }
        
        # Add optional parameters if provided
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
            
        return payload
    
    async def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from OpenAI API response.
        
        Args:
            response: OpenAI API response
            
        Returns:
            str: Extracted content
        """
        return response["choices"][0]["message"]["content"] 