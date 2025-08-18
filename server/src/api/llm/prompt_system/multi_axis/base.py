"""
Base models and functions for multi-axis evaluation templates.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ..prompt_templates import PromptTemplate


class AxisTemplate(BaseModel):
    """Template for an individual evaluation axis."""
    
    name: str = Field(..., description="Name of the evaluation axis")
    description: str = Field(..., description="Description of what this axis evaluates")
    ranking_keyword: str = Field(..., description="Keyword to use for extracting this axis's rating")
    prompt_section: str = Field(..., description="The specific prompt section for this axis")


class MultiAxisTemplate(BaseModel):
    """Template for multi-dimensional evaluation across multiple axes."""
    
    id: str = Field(..., description="Unique identifier for this template")
    name: str = Field(..., description="Human-readable name for this template")
    description: str = Field(..., description="Description of this template's purpose")
    system_intro: str = Field(..., description="Introduction section of the system message")
    system_outro: str = Field(..., description="Conclusion section of the system message")
    axes: List[AxisTemplate] = Field(..., description="List of evaluation axes")
    
    def to_prompt_template(self) -> PromptTemplate:
        """Convert to a standard PromptTemplate for single axis compatibility."""
        # This only returns the first axis for general evaluation
        if not self.axes:
            raise ValueError("MultiAxisTemplate must have at least one axis")
            
        return PromptTemplate(
            id=self.id,
            name=self.name,
            description=self.description,
            system_message=f"{self.system_intro}\n\n{self.axes[0].prompt_section}\n\n{self.system_outro}",
            ranking_keyword=self.axes[0].ranking_keyword
        )


def get_axis_ranking_keywords(template: MultiAxisTemplate) -> Dict[str, str]:
    """
    Get mapping of axis names to their ranking keywords.
    
    Args:
        template: The multi-axis template
        
    Returns:
        Dict mapping axis names to ranking keywords
    """
    return {axis.name: axis.ranking_keyword for axis in template.axes}