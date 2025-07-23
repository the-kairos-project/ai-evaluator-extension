"""
Multi-axis prompt system for AI evaluations.

This package contains templates and functions for evaluating candidates
across multiple dimensions (axes) in a single LLM call.
"""

from .base import (
    AxisTemplate,
    MultiAxisTemplate,
    get_axis_ranking_keywords,
)

from .builder import (
    MultiAxisPromptConfig,
    build_multi_axis_prompt,
)

# Import directly from templates directory
from .templates.academic import ACADEMIC_MULTI_AXIS_TEMPLATE
from .templates.spar import SPAR_MULTI_AXIS_TEMPLATE
from .templates import (
    AVAILABLE_MULTI_AXIS_TEMPLATES,
    get_multi_axis_template,
)

__all__ = [
    # Base Types
    "AxisTemplate",
    "MultiAxisTemplate",
    "get_axis_ranking_keywords",
    
    # Builder
    "MultiAxisPromptConfig",
    "build_multi_axis_prompt",
    
    # Templates
    "ACADEMIC_MULTI_AXIS_TEMPLATE", 
    "SPAR_MULTI_AXIS_TEMPLATE",
    "AVAILABLE_MULTI_AXIS_TEMPLATES",
    "get_multi_axis_template",
]