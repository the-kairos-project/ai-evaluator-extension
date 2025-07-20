"""
LLM module for API proxy and evaluation.

This module provides endpoints for proxying requests to LLM providers
and evaluating applicants using LLMs.
"""

from src.api.llm.proxy import router
from src.api.llm.prompt_system import (
    PromptTemplate, PromptVariables, PromptConfig, 
    build_prompt, get_template, ACADEMIC_TEMPLATE
)
from src.api.llm.providers import (
    BaseProvider, Message, ProviderRequest, ProviderResponse,
    OpenAIProvider, AnthropicProvider, ProviderFactory
)

__all__ = [
    "router",
    # Prompt system
    "PromptTemplate",
    "PromptVariables",
    "PromptConfig",
    "build_prompt",
    "get_template",
    "ACADEMIC_TEMPLATE",
    # Providers
    "BaseProvider",
    "Message",
    "ProviderRequest",
    "ProviderResponse",
    "OpenAIProvider",
    "AnthropicProvider",
    "ProviderFactory",
] 