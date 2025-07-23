"""
Proxy module for LLM API calls and evaluation.

This module provides proxy endpoints for OpenAI and Anthropic API calls,
as well as evaluation functionality with plugin enrichment.
"""

from .router import router
from .models import (
    OpenAIRequest, AnthropicRequest, 
    EvaluationRequest, EvaluationResponse
)
from .enrichment import format_enrichment_data

__all__ = [
    "router",
    "OpenAIRequest",
    "AnthropicRequest",
    "EvaluationRequest",
    "EvaluationResponse",
    "format_enrichment_data"
]