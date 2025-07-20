"""
Base LLM Provider interface and data models.

Design decision: We use an abstract base class to ensure all providers
implement the same interface, making it easy to swap providers without
changing the consuming code. The interface is kept minimal but sufficient
for our use cases.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from src.core.exceptions import ValidationError


class MessageRole(str, Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """Represents a message in the conversation."""
    role: MessageRole
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {"role": self.role.value, "content": self.content}


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    All LLM providers must implement this interface to ensure
    compatibility with the rest of the system.
    """
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize the provider.
        
        Args:
            api_key: API key for authentication
            model: Model identifier
            **kwargs: Provider-specific configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Union[LLMMessage, Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion for the given messages.
        
        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with the generated content
        """
        pass
    
    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Union[LLMMessage, Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """Stream a completion for the given messages.
        
        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Yields:
            Chunks of generated content
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the provider name."""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if the provider supports streaming."""
        pass
    
    @property
    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Check if the provider supports function calling."""
        pass
    
    def _normalize_messages(
        self, 
        messages: List[Union[LLMMessage, Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Normalize messages to dictionary format.
        
        Args:
            messages: List of messages in various formats
            
        Returns:
            List of messages as dictionaries
        """
        normalized = []
        for msg in messages:
            if isinstance(msg, LLMMessage):
                normalized.append(msg.to_dict())
            elif isinstance(msg, dict):
                normalized.append(msg)
            else:
                raise ValidationError(
                    "message",
                    msg,
                    f"Invalid message type: {type(msg)}. Expected LLMMessage or dict"
                )
        return normalized 

    def _format_message(self, msg: LLMMessage) -> Dict[str, Any]:
        """Format a single message for the API.
        
        Args:
            msg: LLMMessage to format
            
        Returns:
            Formatted message dictionary
        """
        if isinstance(msg, LLMMessage):
            return {"role": msg.role.value, "content": msg.content}
        else:
            raise ValidationError(
                "message",
                msg,
                f"Invalid message type: {type(msg)}. Expected LLMMessage"
            ) 