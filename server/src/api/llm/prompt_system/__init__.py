"""
Prompt system package for AI evaluations.

This package contains modules for building and managing prompts for LLM evaluations.
"""

from .models_config import (
    ModelProvider,
    ModelOption,
    OPENAI_MODELS,
    ANTHROPIC_MODELS,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_ANTHROPIC_MODEL,
    MODEL_PROVIDERS,
    PROVIDER_ICONS,
    format_model_name,
    get_model_by_id,
)

from .prompt_templates import (
    PromptTemplate,
    PromptVariables,
    ACADEMIC_TEMPLATE,
    DEFAULT_PROMPT_SETTINGS,
    AVAILABLE_TEMPLATES,
    get_template,
)

from .prompt_builder import (
    Message,
    PromptConfig,
    build_prompt,
    get_ranking_keyword,
)

__all__ = [
    # Models
    "ModelProvider",
    "ModelOption",
    "OPENAI_MODELS",
    "ANTHROPIC_MODELS",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_ANTHROPIC_MODEL",
    "MODEL_PROVIDERS",
    "PROVIDER_ICONS",
    "format_model_name",
    "get_model_by_id",
    
    # Templates
    "PromptTemplate",
    "PromptVariables",
    "ACADEMIC_TEMPLATE",
    "DEFAULT_PROMPT_SETTINGS",
    "AVAILABLE_TEMPLATES",
    "get_template",
    
    # Builder
    "Message",
    "PromptConfig",
    "build_prompt",
    "get_ranking_keyword",
] 