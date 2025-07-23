"""
Multi-axis evaluation templates.

This module provides templates for multi-dimensional evaluation across multiple axes.
Each template is defined in its own file for better organization.
"""

from typing import List, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..base import MultiAxisTemplate
    
# Direct import with aliases for clarity while maintaining original objects
from .academic import ACADEMIC_MULTI_AXIS_TEMPLATE
from .spar import SPAR_MULTI_AXIS_TEMPLATE

# Create aliases for code clarity but don't lose original identity
ACADEMIC_TEMPLATE = ACADEMIC_MULTI_AXIS_TEMPLATE
SPAR_TEMPLATE = SPAR_MULTI_AXIS_TEMPLATE

# List of all available multi-axis templates 
# Type annotation but using 'Any' to avoid circular imports
AVAILABLE_MULTI_AXIS_TEMPLATES = [
    # Deprecated: ACADEMIC kept for backward compatibility only.
    ACADEMIC_MULTI_AXIS_TEMPLATE,
    SPAR_MULTI_AXIS_TEMPLATE,      # Preferred default template
    # Add more templates here as they are created
]

# Default template to use (deprecated academic → SPAR)
DEFAULT_MULTI_AXIS_TEMPLATE = SPAR_MULTI_AXIS_TEMPLATE


def get_multi_axis_template(template_id: str) -> 'MultiAxisTemplate':
    """Get a multi-axis template by ID with fallback to default.

    If template_id is falsy or unknown, return the default SPAR template.
    """
    if not template_id:
        return DEFAULT_MULTI_AXIS_TEMPLATE
    for template in AVAILABLE_MULTI_AXIS_TEMPLATES:
        if template.id == template_id:
            return template
    return DEFAULT_MULTI_AXIS_TEMPLATE