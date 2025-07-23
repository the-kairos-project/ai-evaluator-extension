"""
Multi-axis prompt builder - handles building prompts for multi-dimensional evaluations.
"""

from typing import Dict, List

from ..prompt_templates import PromptVariables
from .base import MultiAxisTemplate
import logging
logger = logging.getLogger(__name__)


class Message(Dict[str, str]):
    """Message format for LLM prompts."""
    pass


class MultiAxisPromptConfig:
    """Configuration for building a multi-axis prompt."""
    
    def __init__(self, template: MultiAxisTemplate, variables: PromptVariables):
        self.template = template
        self.variables = variables


def build_multi_axis_prompt(applicant_data: str, config: MultiAxisPromptConfig) -> List[Message]:
    """
    Build a complete prompt for multi-axis evaluation.
    
    Args:
        applicant_data: The applicant data to evaluate
        config: The multi-axis prompt configuration
        
    Returns:
        List of messages in the format expected by LLM APIs
    """
    template = config.template
    variables = config.variables
    
    # Log detailed information about the template being used
    logger.debug("====================== MULTI-AXIS TEMPLATE DETAILS ======================")
    logger.debug(f"Template ID: {template.id}")
    logger.debug(f"Template Name: {template.name}")
    logger.debug(f"Number of axes: {len(template.axes)}")
    logger.debug(f"Axis names: {[axis.name for axis in template.axes]}")
    logger.debug(f"Ranking keywords: {[axis.ranking_keyword for axis in template.axes]}")
    
    # Build the system message with all axes
    system_message = template.system_intro.replace(
        "{criteria_string}", variables.criteria_string
    )
    
    # Add each axis section
    for axis in template.axes:
        axis_section = axis.prompt_section.replace(
            "{ranking_keyword}", axis.ranking_keyword
        )
        system_message += f"\n\n{axis_section}"
    
    # Add the conclusion section
    system_message += f"\n\n{template.system_outro}"
    
    # Add additional instructions if provided
    if variables.additional_instructions and variables.additional_instructions.strip():
        system_message = system_message.replace(
            "{additional_instructions}",
            f"\n\n{variables.additional_instructions.strip()}"
        )
    else:
        system_message = system_message.replace("{additional_instructions}", "")
    
    # Put system message first to establish the context properly
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": applicant_data},
    ]