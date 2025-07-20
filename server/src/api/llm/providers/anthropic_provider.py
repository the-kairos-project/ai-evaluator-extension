"""
Anthropic provider implementation.
"""

from typing import Dict, Any, List

from .base import BaseProvider, ProviderRequest, Message


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
        # Check if the last message is a system message
        messages = request.messages
        last_message_is_system = len(messages) > 0 and messages[-1].role == "system"
        
        # Prepare request payload
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
        }
        
        # Handle system message specially
        if last_message_is_system:
            payload["messages"] = [{"role": msg.role, "content": msg.content} for msg in messages[:-1]]
            payload["system"] = messages[-1].content
        else:
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