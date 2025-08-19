"""
OpenAI LLM Provider implementation.
"""

from typing import List, Dict, Any, Optional, Union
from src.utils.logging import get_structured_logger
from openai import AsyncOpenAI

from .base import LLMProvider, LLMResponse, LLMMessage
from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-5-mini", **kwargs):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-5-mini)
            **kwargs: Additional configuration (base_url, organization, etc.)
        """
        super().__init__(api_key, model, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=kwargs.get("base_url"),
            organization=kwargs.get("organization"),
        )
    
    async def complete(
        self,
        messages: List[Union[LLMMessage, Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion using OpenAI API.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters
            
        Returns:
            LLMResponse with the completion
        """
        try:
            normalized_messages = self._normalize_messages(messages)
            
            # Build request parameters
            params = {
                "model": self.model,
                "messages": normalized_messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
                
            # Add any additional OpenAI-specific parameters
            params.update(kwargs)
            
            # Make API call
            response = await self.client.chat.completions.create(**params)
            
            # Extract response
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "id": response.id,
                }
            )
            
        except Exception as e:
            logger.error("OpenAI completion failed", error=str(e))
            raise
    
    async def stream_complete(
        self,
        messages: List[Union[LLMMessage, Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """Stream a completion using OpenAI API.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters
            
        Yields:
            Chunks of generated content
        """
        try:
            normalized_messages = self._normalize_messages(messages)
            
            # Build request parameters
            params = {
                "model": self.model,
                "messages": normalized_messages,
                "temperature": temperature,
                "stream": True,
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
                
            # Add any additional OpenAI-specific parameters
            params.update(kwargs)
            
            # Make streaming API call
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("OpenAI streaming failed", error=str(e))
            raise
    
    @property
    def name(self) -> str:
        """Get provider name."""
        return "openai"
    
    @property
    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True
    
    @property
    def supports_function_calling(self) -> bool:
        """OpenAI supports function calling."""
        return True 