"""
Evaluation functionality for LLM proxy.

This module handles the evaluation of applicants using LLMs,
including prompt building and score extraction for both single-axis
and multi-axis evaluations.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple, List, Union

from src.api.llm.prompt_system import (
    PromptTemplate, PromptVariables, PromptConfig,
    build_prompt,
    MultiAxisPromptConfig,
    build_multi_axis_prompt, get_multi_axis_template,
    get_axis_ranking_keywords
)
from src.api.llm.proxy.models import AxisScore

logger = logging.getLogger(__name__)


async def build_evaluation_prompt(
    applicant_data: str,
    criteria_string: str,
    template_id: str,
    ranking_keyword: Optional[str],
    additional_instructions: Optional[str],
    custom_template: Optional[PromptTemplate],
    enrichment_data: Optional[Dict[str, Any]] = None,
    use_multi_axis: bool = False
) -> Tuple[List[Dict[str, str]], Union[str, Dict[str, str]]]:
    """Build the evaluation prompt.
    
    Args:
        applicant_data: Applicant data to evaluate
        criteria_string: Evaluation criteria
        template_id: Template ID to use
        ranking_keyword: Ranking keyword
        additional_instructions: Additional instructions
        custom_template: Custom template
        enrichment_data: Optional enrichment data
        
    Returns:
        Tuple of (messages, ranking_keyword)
    """
    # Process criteria string
    processed_criteria_string = criteria_string.replace("<br>", "\n")
    
    if use_multi_axis:
        # Get the multi-axis template
        multi_template = get_multi_axis_template(template_id)
        logger.debug(f"Using multi-axis template: {multi_template.id} - {multi_template.name}")
        
        # Create variables for template substitution
        variables = PromptVariables(
            criteria_string=processed_criteria_string,
            ranking_keyword=ranking_keyword,  # This is ignored for multi-axis
            additional_instructions=additional_instructions or ""
        )
        
        # Build the multi-axis prompt
        config = MultiAxisPromptConfig(template=multi_template, variables=variables)
        messages = build_multi_axis_prompt(applicant_data, config)
        logger.debug(f"Built multi-axis prompt with {len(messages)} messages")
        
        # Get all axis ranking keywords for score extraction
        axis_keywords = get_axis_ranking_keywords(multi_template)
        logger.debug(f"Using axis keywords: {axis_keywords}")
        
        return messages, axis_keywords
    else:
        # Standard single-axis evaluation derived from the multi-axis template's first axis
        # Always use SPAR multi-axis as source and collapse to first axis for single-axis mode
        multi_template = get_multi_axis_template("multi_axis_spar")
        template_from_first_axis = multi_template.to_prompt_template()
        logger.debug(
            f"Using single-axis derived from multi-axis: {template_from_first_axis.id} - {template_from_first_axis.name}"
        )

        # Create variables for template substitution
        variables = PromptVariables(
            criteria_string=processed_criteria_string,
            ranking_keyword=ranking_keyword or template_from_first_axis.ranking_keyword,
            additional_instructions=additional_instructions or ""
        )

        # Build the prompt
        config = PromptConfig(template=template_from_first_axis, variables=variables)
        messages = build_prompt(applicant_data, config)
        logger.debug(f"Built single-axis prompt (from multi-axis) with {len(messages)} messages")

        # Get the ranking keyword for score extraction
        final_ranking_keyword = variables.ranking_keyword or template_from_first_axis.ranking_keyword
        logger.debug(f"Using ranking keyword: {final_ranking_keyword}")

        return messages, final_ranking_keyword


def extract_score(text: str, ranking_keyword: str) -> Optional[int]:
    """Extract a single score from the LLM response.
    
    Args:
        text: LLM response text
        ranking_keyword: Keyword to look for
        
    Returns:
        Optional[int]: Extracted score or None if not found
    """
    try:
        # Look for the ranking keyword followed by a number
        pattern = f"{ranking_keyword}[^0-9]*([1-5])"
        match = re.search(pattern, text)
        
        if not match:
            return None
        
        score = int(match.group(1))
        
        # Validate score is between 1 and 5
        if 1 <= score <= 5:
            return score
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting score: {str(e)}")
        return None


def extract_multi_axis_scores(text: str, axis_keywords: Dict[str, str]) -> List[AxisScore]:
    """Extract scores for multiple axes from the LLM response.
    
    Args:
        text: LLM response text
        axis_keywords: Dictionary mapping axis names to their ranking keywords
        
    Returns:
        List[AxisScore]: List of extracted axis scores
    """
    axis_scores = []
    
    try:
        
        for axis_name, keyword in axis_keywords.items():
            # First, try the exact ranking keyword
            pattern = f"{keyword}[^0-9]*([1-5])"
            match = re.search(pattern, text)
            
            if match:
                score = int(match.group(1))
                
                # Validate score is between 1 and 5
                if 1 <= score <= 5:
                    axis_scores.append(AxisScore(name=axis_name, score=score))
                    continue
            # Fallback to general patterns if no valid match found
            
            # Try a more general pattern as fallback using the axis name
            
            # List of patterns to try, from most specific to most general
            patterns = [
                # Original keyword formats
                f"{keyword}\\s*=\\s*([1-5])",                          # GENERAL_PROMISE_RATING = 4
                f"{keyword}:\\s*([1-5])",                              # GENERAL_PROMISE_RATING: 4
                
                # Try the keyword in various formats
                f"{keyword}\\s*-\\s*([1-5])",                          # GENERAL_PROMISE_RATING - 4
                f"{keyword}.*?([1-5])/5",                              # GENERAL_PROMISE_RATING ... 4/5
                
                # Try the axis name with RATING suffix in various formats
                f"{axis_name.upper()}_RATING\\s*=\\s*([1-5])",         # GENERAL_PROMISE_RATING = 4
                f"{axis_name.upper()}_RATING:\\s*([1-5])",             # GENERAL_PROMISE_RATING: 4
                f"{axis_name}_RATING\\s*=\\s*([1-5])",                 # General_Promise_RATING = 4
                f"{axis_name}_RATING:\\s*([1-5])",                     # General_Promise_RATING: 4
                
                # Try just the axis name in uppercase
                f"{axis_name.upper()}\\s*=\\s*([1-5])",                # GENERAL_PROMISE = 4
                f"{axis_name.upper()}:\\s*([1-5])",                    # GENERAL_PROMISE: 4
                
                # Try the axis name with FINAL_RANKING format
                f"FINAL_RANKING for {axis_name}\\s*=\\s*([1-5])",      # FINAL_RANKING for General Promise = 4
                
                # Try "X = Y" format (common in responses)
                f"{axis_name}\\s*=\\s*([1-5])",                        # General Promise = 4
                
                # Try colon format
                f"{axis_name}:\\s*([1-5])",                            # General Promise: 4
                
                # Try axis name with Rating suffix
                f"{axis_name} Rating\\s*=\\s*([1-5])",                 # General Promise Rating = 4
                f"{axis_name} Rating:\\s*([1-5])",                     # General Promise Rating: 4
                
                # Try finding any line with the axis name and a number
                f"{axis_name}.*?([1-5])\\s*(/5|out of 5)?",            # General Promise ... 4
                
                # Ultra permissive patterns
                f"(?i){axis_name}.*?([1-5])",                          # case insensitive
                f"(?i)\\b{axis_name}\\b.*?([1-5])\\b",                 # word boundaries
                f"(?i)score for {axis_name}.*?([1-5])"                 # "score for X is Y"
            ]
            
            # Try each pattern in order
            found = False
            for i, pattern in enumerate(patterns):
                fallback_match = re.search(pattern, text)
                if fallback_match:
                    score = int(fallback_match.group(1))
                    if 1 <= score <= 5:
                        axis_scores.append(AxisScore(name=axis_name, score=score))
                        found = True
                        break
            # If we still couldn't find a score, try more aggressive section-based extraction
            if not found:
                
                # Try to find a section that contains the axis name in various formats
                section_patterns = [
                    # Standard markdown headers
                    f"(?i)##\\s*{axis_name}[\\s\\S]*?([1-5])(?:[^0-9]|$)",                      # ## General Promise ... 4
                    f"(?i)###\\s*{axis_name}[\\s\\S]*?([1-5])(?:[^0-9]|$)",                     # ### General Promise ... 4
                    
                    # Bold formatting
                    f"(?i)\\*\\*{axis_name}\\*\\*[\\s\\S]*?([1-5])(?:[^0-9]|$)",                # **General Promise** ... 4
                    f"(?i)\\*\\*{axis_name}:[^*]*\\*\\*[\\s\\S]*?([1-5])(?:[^0-9]|$)",          # **General Promise:** ... 4
                    
                    # Section with heading
                    f"(?i){axis_name}\\s*assessment[\\s\\S]*?([1-5])(?:[^0-9]|$)",              # General Promise assessment ... 4
                    f"(?i){axis_name}\\s*evaluation[\\s\\S]*?([1-5])(?:[^0-9]|$)",              # General Promise evaluation ... 4
                    
                    # More permissive patterns
                    f"(?i){axis_name}[^#\\*]*?\\b([1-5])\\b",                                   # General Promise ... 4
                    f"(?i)\\b{axis_name}\\b[\\s\\S]{{0,500}}?\\bscore\\b[\\s\\S]{{0,50}}?([1-5])",  # Limited context around "score"
                    
                    # Rating-specific patterns
                    f"(?i)\\b{axis_name}\\b[\\s\\S]{{0,500}}?\\brating\\b[\\s\\S]{{0,50}}?([1-5])",  # Limited context around "rating"
                    f"(?i)\\b{axis_name}\\b[\\s\\S]{{0,500}}?\\b([1-5])/5\\b"                   # Score with denominator
                ]
                
                for i, pattern in enumerate(section_patterns):
                    section_match = re.search(pattern, text)
                    if section_match:
                        score = int(section_match.group(1))
                        if 1 <= score <= 5:
                            axis_scores.append(AxisScore(name=axis_name, score=score))
                            found = True
                            break
                # No else case needed, fallback continues below
                
                # If still not found, try splitting text into paragraphs
                if not found:
                    paragraphs = re.split(r'\n\n+', text)
                    for paragraph in paragraphs:
                        if axis_name.lower() in paragraph.lower():
                            number_match = re.search(r'\b([1-5])\b', paragraph)
                            if number_match:
                                score = int(number_match.group(1))
                                if 1 <= score <= 5:
                                    axis_scores.append(AxisScore(name=axis_name, score=score))
                                    found = True
                                    break
                
            # If all patterns failed, add a null score
            if not found:
                axis_scores.append(AxisScore(name=axis_name, score=None))
        
        return axis_scores
            
    except Exception as e:
        logger.error(f"Error extracting multi-axis scores: {str(e)}")
        import traceback
        traceback.print_exc()
        return [AxisScore(name=name, score=None) for name in axis_keywords.keys()]