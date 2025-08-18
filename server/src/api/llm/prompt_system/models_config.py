"""
Models configuration file.

This module centralizes all model definitions and makes it easy to update them
when new models are released or old ones are deprecated.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class ModelProvider(str, Enum):
    """Available model providers."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelOption(BaseModel):
    """Model type definition."""
    
    label: str
    value: str
    description: str
    emoji: str
    is_available: bool


# OpenAI Models (Updated May 2025)
OPENAI_MODELS = [
    ModelOption(
        label="GPT-4.1",
        value="gpt-4.1",
        description="Successor to GPT-4 Turbo, highly capable flagship model",
        emoji="🚀",
        is_available=True,
    ),
    ModelOption(
        label="GPT-4o",
        value="gpt-4o",
        description="Latest multimodal model with advanced capabilities",
        emoji="⭐",
        is_available=True,
    ),
    ModelOption(
        label="GPT-4o mini",
        value="gpt-4o-mini",
        description="Fast, cost-effective version of GPT-4o",
        emoji="💡",
        is_available=True,
    ),
]

# Get default OpenAI model (using gpt-4o-mini for cost efficiency)
DEFAULT_OPENAI_MODEL = OPENAI_MODELS[2].value  # gpt-4o-mini

# Anthropic Models (Updated May 2025)
ANTHROPIC_MODELS = [
    ModelOption(
        label="Claude Opus 4",
        value="claude-opus-4-20250514",
        description="Latest most capable model from Anthropic",
        emoji="✨",
        is_available=True,
    ),
    ModelOption(
        label="Claude Sonnet 4",
        value="claude-sonnet-4-20250514",
        description="Latest balanced model from Anthropic",
        emoji="🏆",
        is_available=True,
    ),
    ModelOption(
        label="Claude 3.5 Haiku",
        value="claude-3-5-haiku-20241022",
        description="Latest fast and cost-effective model from Anthropic",
        emoji="💨",
        is_available=True,
    ),
]

# Get default Anthropic model (using haiku for cost efficiency)
DEFAULT_ANTHROPIC_MODEL = ANTHROPIC_MODELS[2].value


class ProviderConfig(BaseModel):
    """Configuration for a model provider."""
    
    id: str
    name: str
    emoji: str
    models: List[ModelOption]
    default_model: str


MODEL_PROVIDERS = [
    ProviderConfig(
        id="openai",
        name="OpenAI",
        emoji="🤖",
        models=OPENAI_MODELS,
        default_model=DEFAULT_OPENAI_MODEL,
    ),
    ProviderConfig(
        id="anthropic",
        name="Anthropic Claude",
        emoji="🧠",
        models=ANTHROPIC_MODELS,
        default_model=DEFAULT_ANTHROPIC_MODEL,
    ),
]

# Get a dictionary of emoji icons for each provider
PROVIDER_ICONS = {
    "openai": "🤖",
    "anthropic": "🧠",
}


def format_model_name(model_id: str) -> str:
    """Format a model ID into a user-friendly name."""
    for model in OPENAI_MODELS:
        if model.value == model_id:
            return model.label
    
    for model in ANTHROPIC_MODELS:
        if model.value == model_id:
            return model.label
    
    return model_id


def get_model_by_id(provider: str, model_id: str) -> Optional[ModelOption]:
    """Get a model by provider and ID."""
    if provider == ModelProvider.OPENAI:
        for model in OPENAI_MODELS:
            if model.value == model_id:
                return model
    elif provider == ModelProvider.ANTHROPIC:
        for model in ANTHROPIC_MODELS:
            if model.value == model_id:
                return model
    return None 