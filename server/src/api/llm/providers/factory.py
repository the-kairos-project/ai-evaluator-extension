"""
Provider factory module.

This module provides a factory for creating provider instances.
"""

from typing import Dict, Type

from .base import BaseProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


class ProviderFactory:
    """Factory for creating provider instances."""
    
    _providers: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_name: str) -> BaseProvider:
        """Get a provider instance by name.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            BaseProvider: Provider instance
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            supported = ", ".join(cls._providers.keys())
            raise ValueError(f"Unsupported provider: {provider_name}. Supported providers: {supported}")
        
        return provider_class()
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a new provider.
        
        Args:
            name: Name of the provider
            provider_class: Provider class
        """
        cls._providers[name.lower()] = provider_class 