"""
Prompt template system for AI evaluations.
This module contains all prompt templates and their configurations.
"""
from typing import Optional
from pydantic import BaseModel


class PromptTemplate(BaseModel):
    """Prompt template model."""
    
    id: str
    name: str
    description: str
    system_message: str
    ranking_keyword: str
    additional_instructions: Optional[str] = ""


class PromptVariables(BaseModel):
    """Variables that can be substituted in prompt templates."""
    
    criteria_string: str
    ranking_keyword: Optional[str] = None
    additional_instructions: Optional[str] = None


# Default template - extracted from existing proven prompt
ACADEMIC_TEMPLATE = PromptTemplate(
    id="academic",
    name="Academic Evaluation",
    description="Current proven template for academic/course applications",
    system_message="""Evaluate the application above, based on the following rubric: {criteria_string}

You should ignore general statements or facts about the world, and focus on what the applicant themselves has achieved. You do not need to structure your assessment similar to the answers the user has given.

IMPORTANT RATING CONSTRAINTS:
- Your rating MUST be an integer (whole number only)
- Your rating MUST be between 1 and 5 (inclusive)
- DO NOT use ratings above 5 or below 1
- If the rubric mentions different scale values, convert them to the 1-5 scale

First explain your reasoning thinking step by step. Then output your final answer by stating '{ranking_keyword} = ' and then the relevant integer between 1 and 5.{additional_instructions}""",
    ranking_keyword="FINAL_RANKING"
)

# Default settings for new installations
DEFAULT_PROMPT_SETTINGS = {
    "selected_template": ACADEMIC_TEMPLATE.id,
    "custom_template": None,
    "ranking_keyword": ACADEMIC_TEMPLATE.ranking_keyword,
    "additional_instructions": "",
}

# Available templates (starting with just one)
AVAILABLE_TEMPLATES = [ACADEMIC_TEMPLATE]


def get_template(template_id: str) -> PromptTemplate:
    """Get template by ID with fallback to default."""
    for template in AVAILABLE_TEMPLATES:
        if template.id == template_id:
            return template
    return ACADEMIC_TEMPLATE 