"""
LLM Provider Factory for dynamic provider selection.

Design decision: We use a factory pattern to encapsulate provider
instantiation logic and make it easy to add new providers. The factory
uses provider names as keys for simple configuration.
"""

from typing import Dict, Type, Optional, Any
import structlog

from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from src.core.exceptions import ConfigurationError

logger = structlog.get_logger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    # Registry of available providers
    _providers: Dict[str, Type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """Register a new provider.
        
        Args:
            name: Provider name (e.g., "openai", "anthropic")
            provider_class: Provider class that implements LLMProvider
        """
        cls._providers[name.lower()] = provider_class
        logger.info("Registered LLM provider", provider=name)
    
    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """Create an LLM provider instance.
        
        Args:
            provider_name: Name of the provider (e.g., "openai", "anthropic")
            api_key: API key for authentication
            model: Model to use (optional, uses provider default if not specified)
            **kwargs: Additional provider-specific configuration
            
        Returns:
            Configured LLMProvider instance
            
        Raises:
            ConfigurationError: If provider is not found or configuration is invalid
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ConfigurationError(
                "llm_provider",
                f"Unknown provider '{provider_name}'. Available: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        
        try:
            if model:
                provider = provider_class(api_key=api_key, model=model)
            else:
                provider = provider_class(api_key=api_key)
            
            logger.info(
                "Created LLM provider",
                provider=provider_name,
                model=provider.model
            )
            
            return provider
            
        except Exception as e:
            raise ConfigurationError(
                "llm_provider",
                f"Failed to create {provider_name} provider: {str(e)}"
            )
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[LLMProvider]]:
        """Get all available providers.
        
        Returns:
            Dictionary of provider names to provider classes
        """
        return cls._providers.copy()
    
    @classmethod
    def get_provider_info(cls, provider_name: str) -> Dict[str, Any]:
        """Get information about a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider information including capabilities
            
        Raises:
            ConfigurationError: If provider not found
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            raise ConfigurationError(
                "llm_provider",
                f"Unknown provider '{provider_name}'"
            )
        
        # Create a temporary instance to get capabilities
        # This is safe as we're not making any API calls
        temp_provider = cls._providers[provider_name](api_key="dummy", model="dummy")
        
        return {
            "name": temp_provider.name,
            "supports_streaming": temp_provider.supports_streaming,
            "supports_function_calling": temp_provider.supports_function_calling,
            "class": cls._providers[provider_name].__name__,
        } 