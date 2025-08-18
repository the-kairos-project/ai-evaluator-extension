"""
Prompt builder - handles template variable substitution and prompt construction.
"""
from typing import List, TypedDict

from .prompt_templates import PromptTemplate, PromptVariables


class Message(TypedDict):
    """Message format for LLM prompts."""
    
    role: str
    content: str


class PromptConfig:
    """Configuration for building a prompt."""
    
    def __init__(self, template: PromptTemplate, variables: PromptVariables):
        self.template = template
        self.variables = variables


def build_prompt(applicant_data: str, config: PromptConfig) -> List[Message]:
    """
    Build a complete prompt from template and variables.
    
    Args:
        applicant_data: The applicant data to evaluate
        config: The prompt configuration with template and variables
        
    Returns:
        List of messages in the format expected by LLM APIs
    """
    template = config.template
    variables = config.variables
    
    # Substitute variables in the system message
    system_message = template.system_message.replace(
        "{criteria_string}", variables.criteria_string
    ).replace(
        "{ranking_keyword}", 
        variables.ranking_keyword or template.ranking_keyword
    )
    
    # Add additional instructions if provided
    if variables.additional_instructions and variables.additional_instructions.strip():
        system_message = system_message.replace(
            "{additional_instructions}",
            f"\n\n{variables.additional_instructions.strip()}"
        )
    else:
        system_message = system_message.replace("{additional_instructions}", "")
    
    return [
        {"role": "user", "content": applicant_data},
        {"role": "system", "content": system_message},
    ]


def get_ranking_keyword(config: PromptConfig) -> str:
    """
    Get the ranking keyword for result extraction.
    
    Args:
        config: The prompt configuration
        
    Returns:
        The ranking keyword to use for extracting scores
    """
    return config.variables.ranking_keyword or config.template.ranking_keyword 