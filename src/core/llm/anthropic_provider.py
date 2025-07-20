"""
Anthropic (Claude) LLM Provider implementation.
"""

from typing import List, Dict, Optional, Union
import structlog
from anthropic import AsyncAnthropic

from .base import LLMProvider, LLMResponse, LLMMessage

logger = structlog.get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", **kwargs):
        """Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-opus-20240229)
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)
        client_kwargs = {"api_key": api_key}
        if kwargs.get("base_url"):
            client_kwargs["base_url"] = kwargs["base_url"]
        self.client = AsyncAnthropic(**client_kwargs)
        # Default max tokens for Claude
        self.default_max_tokens = kwargs.get("default_max_tokens", 4096)
    
    async def complete(
        self,
        messages: List[Union[LLMMessage, Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion using Anthropic API.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic-specific parameters
            
        Returns:
            LLMResponse with the completion
        """
        try:
            normalized_messages = self._normalize_messages(messages)
            
            # Anthropic requires system message to be separate
            system_message = None
            user_messages = []
            
            for msg in normalized_messages:
                if msg["role"] == "system":
                    # Anthropic only supports one system message
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            # Build request parameters
            params = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            }
            
            if system_message:
                params["system"] = system_message
                
            # Add any additional Anthropic-specific parameters
            params.update(kwargs)
            
            # Make API call
            response = await self.client.messages.create(**params)
            
            # Extract response
            content = response.content[0].text if response.content else ""
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            } if hasattr(response, 'usage') else None
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                metadata={
                    "stop_reason": response.stop_reason,
                    "id": response.id,
                }
            )
            
        except Exception as e:
            logger.error("Anthropic completion failed", error=str(e))
            raise
    
    async def stream_complete(
        self,
        messages: List[Union[LLMMessage, Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """Stream a completion using Anthropic API.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic-specific parameters
            
        Yields:
            Chunks of generated content
        """
        try:
            normalized_messages = self._normalize_messages(messages)
            
            # Anthropic requires system message to be separate
            system_message = None
            user_messages = []
            
            for msg in normalized_messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            # Build request parameters
            params = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
                "stream": True,
            }
            
            if system_message:
                params["system"] = system_message
                
            # Add any additional Anthropic-specific parameters
            params.update(kwargs)
            
            # Make streaming API call
            stream = await self.client.messages.create(**params)
            async for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    yield chunk.delta.text
                    
        except Exception as e:
            logger.error("Anthropic streaming failed", error=str(e))
            raise
    
    @property
    def name(self) -> str:
        """Get provider name."""
        return "anthropic"
    
    @property
    def supports_streaming(self) -> bool:
        """Indicates if the provider supports streaming responses."""
        return True
    
    @property
    def supports_function_calling(self) -> bool:
        """Indicates if the provider supports function calling."""
        return False 