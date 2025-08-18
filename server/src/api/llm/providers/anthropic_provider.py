"""
Anthropic provider implementation.
"""

from typing import Dict, Any

from .base import BaseProvider, ProviderRequest


class AnthropicProvider(BaseProvider):
    """Anthropic provider implementation."""
    
    async def get_api_url(self) -> str:
        """Get the API URL for Anthropic.
        
        Returns:
            str: Anthropic API URL
        """
        return "https://api.anthropic.com/v1/messages"
    
    async def prepare_headers(self, request: ProviderRequest) -> Dict[str, str]:
        """Prepare the request headers for Anthropic API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            Dict[str, str]: Prepared request headers
        """
        return {
            "x-api-key": request.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "anthropic-dangerous-direct-browser-access": "true",
        }
    
    async def prepare_request(self, request: ProviderRequest) -> Dict[str, Any]:
        """Prepare the request payload for Anthropic API.
        
        Args:
            request: Provider request parameters
            
        Returns:
            Dict[str, Any]: Prepared request payload
        """
        # Prepare request payload
        messages = request.messages
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
        }

        # Anthropic Messages API expects a top-level `system` field rather than a
        # message with role "system". Under strict mode we require callers to
        # provide `request.system` (BaseProvider.generate enforces this). Use the
        # provided top-level system and convert remaining messages as-is.
        if not getattr(request, "system", None):
            # Defensive: this should be caught earlier in BaseProvider.generate,
            # but provide a clearer error here if somehow reached.
            raise ValueError("Anthropic provider requires a top-level 'system' field on ProviderRequest")

        payload["system"] = request.system
        payload["messages"] = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Add optional parameters if provided
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
            
        return payload
    
    async def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from Anthropic API response.
        
        Args:
            response: Anthropic API response
            
        Returns:
            str: Extracted content
        """
        return response["content"][0]["text"] 