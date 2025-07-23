"""
Request and response models for LLM proxy endpoints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.api.llm.prompt_system import PromptTemplate


class OpenAIRequest(BaseModel):
    """OpenAI API request model."""
    
    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field(..., description="OpenAI model name")
    messages: List[Dict[str, str]] = Field(..., description="Messages to send to OpenAI")
    max_tokens: Optional[int] = Field(500, description="Maximum number of tokens to generate")
    temperature: Optional[float] = Field(None, description="Temperature for sampling")
    top_p: Optional[float] = Field(None, description="Top-p sampling")
    frequency_penalty: Optional[float] = Field(None, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, description="Presence penalty")
    stop: Optional[list] = Field(None, description="Stop sequences")


class AnthropicRequest(BaseModel):
    """Anthropic API request model."""
    
    api_key: str = Field(..., description="Anthropic API key")
    model: str = Field(..., description="Anthropic model name")
    messages: List[Dict[str, str]] = Field(..., description="Messages to send to Anthropic")
    max_tokens: Optional[int] = Field(500, description="Maximum number of tokens to generate")
    temperature: Optional[float] = Field(None, description="Temperature for sampling")
    top_p: Optional[float] = Field(None, description="Top-p sampling")
    stop_sequences: Optional[list] = Field(None, description="Stop sequences")


class EvaluationRequest(BaseModel):
    """Request model for applicant evaluation."""
    
    api_key: str = Field(..., description="API key for the selected provider")
    provider: str = Field(..., description="Provider to use (openai or anthropic)")
    model: str = Field(..., description="Model name to use")
    applicant_data: str = Field(..., description="Applicant data to evaluate")
    criteria_string: str = Field(..., description="Evaluation criteria")
    template_id: Optional[str] = Field(None, description="Template ID to use (optional; ignored when multi-axis is disabled since we default to SPAR first axis)")
    custom_template: Optional[PromptTemplate] = Field(None, description="Custom template")
    ranking_keyword: Optional[str] = Field(None, description="Ranking keyword")
    additional_instructions: Optional[str] = Field(None, description="Additional instructions")
    
    # Multi-axis evaluation
    use_multi_axis: bool = Field(False, description="Whether to use multi-axis evaluation")
    
    # Plugin enrichment fields
    use_plugin: bool = Field(False, description="Whether to use plugin enrichment")
    source_url: Optional[str] = Field(None, description="URL of the source to enrich (LinkedIn profile, PDF, etc.)")
    pdf_url: Optional[str] = Field(None, description="URL of the PDF resume to enrich (specifically for PDF enrichment)")
    
    # PDF content field (for future use if needed)
    pdf_content: Optional[str] = Field(None, description="Base64 encoded PDF content")


class AxisScore(BaseModel):
    """Model for an individual axis score."""
    
    name: str = Field(..., description="Name of the evaluation axis")
    score: Optional[int] = Field(None, description="Score for this axis (1-5)")


class EvaluationResponse(BaseModel):
    """Response model for applicant evaluation."""
    
    result: str = Field(..., description="Evaluation result")
    score: Optional[int] = Field(None, description="Extracted score (for backward compatibility)")
    scores: Optional[List[AxisScore]] = Field(None, description="Scores for each evaluation axis")
    provider: str = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")