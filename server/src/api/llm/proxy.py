"""LLM proxy endpoints for OpenAI and Anthropic."""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.auth import get_current_active_user, User
from src.config.settings import settings
from src.api.llm.prompt_system import (
    PromptTemplate, PromptVariables, PromptConfig, 
    build_prompt, get_template, ACADEMIC_TEMPLATE
)
from src.api.llm.providers import (
    Message, ProviderRequest, ProviderResponse, ProviderFactory
)

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/llm", tags=["llm"])


class OpenAIRequest(BaseModel):
    """OpenAI API request model."""
    
    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field(..., description="OpenAI model name")
    messages: List[Message] = Field(..., description="Messages to send to OpenAI")
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
    messages: List[Message] = Field(..., description="Messages to send to Anthropic")
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
    template_id: Optional[str] = Field("academic", description="Template ID to use")
    custom_template: Optional[PromptTemplate] = Field(None, description="Custom template")
    ranking_keyword: Optional[str] = Field(None, description="Ranking keyword")
    additional_instructions: Optional[str] = Field(None, description="Additional instructions")


class EvaluationResponse(BaseModel):
    """Response model for applicant evaluation."""
    
    result: str = Field(..., description="Evaluation result")
    score: Optional[int] = Field(None, description="Extracted score")
    provider: str = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")


@router.post("/openai", status_code=status.HTTP_200_OK)
async def proxy_openai(
    request: OpenAIRequest, 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Proxy requests to OpenAI API.
    
    Args:
        request: OpenAI request parameters
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: OpenAI API response
        
    Raises:
        HTTPException: If the request fails
    """
    logger.info(f"OpenAI proxy request received for model: {request.model}")
    logger.debug(f"User: {current_user.username}, Model: {request.model}, Messages: {len(request.messages)}")
    
    try:
        # Get OpenAI provider
        provider = ProviderFactory.get_provider("openai")
        
        # Convert request to provider request
        provider_request = ProviderRequest(
            api_key=request.api_key,
            model=request.model,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )
        
        # Call provider
        response = await provider.call(provider_request)
        
        # Log success
        logger.info(f"OpenAI proxy request successful for model: {request.model}")
        
        # Return raw response
        return response.raw_response
        
    except ValueError as e:
        # Provider not supported
        logger.error(f"Provider error in OpenAI proxy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions with logging
        logger.error(f"HTTP error in OpenAI proxy: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error in OpenAI proxy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/anthropic", status_code=status.HTTP_200_OK)
async def proxy_anthropic(
    request: AnthropicRequest, 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Proxy requests to Anthropic API.
    
    Args:
        request: Anthropic request parameters
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: Anthropic API response
        
    Raises:
        HTTPException: If the request fails
    """
    logger.info(f"Anthropic proxy request received for model: {request.model}")
    logger.debug(f"User: {current_user.username}, Model: {request.model}, Messages: {len(request.messages)}")
    
    try:
        # Get Anthropic provider
        provider = ProviderFactory.get_provider("anthropic")
        
        # Convert request to provider request
        provider_request = ProviderRequest(
            api_key=request.api_key,
            model=request.model,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )
        
        # Call provider
        response = await provider.call(provider_request)
        
        # Log success
        logger.info(f"Anthropic proxy request successful for model: {request.model}")
        
        # Return raw response
        return response.raw_response
        
    except ValueError as e:
        # Provider not supported
        logger.error(f"Provider error in Anthropic proxy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions with logging
        logger.error(f"HTTP error in Anthropic proxy: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error in Anthropic proxy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_applicant(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_active_user)
) -> EvaluationResponse:
    """Evaluate an applicant using the specified provider and model.
    
    This endpoint handles the entire evaluation process:
    1. Builds the prompt using the template system
    2. Sends the request to the appropriate provider
    3. Extracts the score from the response
    4. Returns the result
    
    Args:
        request: Evaluation request parameters
        current_user: Current authenticated user
        
    Returns:
        EvaluationResponse: Evaluation result with extracted score
        
    Raises:
        HTTPException: If the evaluation fails
    """
    logger.info(f"Evaluation request received for provider: {request.provider}, model: {request.model}")
    logger.debug(f"User: {current_user.username}, Template: {request.template_id}, Data length: {len(request.applicant_data)}")
    
    try:
        # Get the template (custom or from library)
        template = request.custom_template if request.custom_template else get_template(request.template_id)
        logger.debug(f"Using template: {template.id} - {template.name}")
        
        # Create variables for template substitution
        variables = PromptVariables(
            criteria_string=request.criteria_string,
            ranking_keyword=request.ranking_keyword or template.ranking_keyword,
            additional_instructions=request.additional_instructions or ""
        )
        
        # Build the prompt
        config = PromptConfig(template=template, variables=variables)
        messages = build_prompt(request.applicant_data, config)
        logger.debug(f"Built prompt with {len(messages)} messages")
        
        # Get the ranking keyword for score extraction
        ranking_keyword = variables.ranking_keyword or template.ranking_keyword
        logger.debug(f"Using ranking keyword: {ranking_keyword}")
        
        # Get provider
        try:
            provider = ProviderFactory.get_provider(request.provider)
            logger.debug(f"Using provider: {provider.name}")
        except ValueError as e:
            logger.error(f"Invalid provider in evaluation request: {request.provider}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Create provider request
        provider_request = ProviderRequest(
            api_key=request.api_key,
            model=request.model,
            messages=[Message(role=msg["role"], content=msg["content"]) for msg in messages],
            max_tokens=500,
            temperature=0.2  # Lower temperature for more consistent evaluations
        )
        
        # Call provider
        logger.info(f"Calling {provider.name} for evaluation")
        response = await provider.call(provider_request)
        result = response.content
        logger.debug(f"Received response with {len(result)} characters")
        
        # Extract score from result
        score = None
        for line in result.split("\n"):
            if ranking_keyword in line:
                try:
                    # Find the score after the ranking keyword
                    score_part = line.split(f"{ranking_keyword} =")[1].strip()
                    # Extract the first number
                    score = int(''.join(filter(str.isdigit, score_part[:2])))
                    logger.info(f"Extracted score: {score}")
                    break
                except (IndexError, ValueError) as e:
                    logger.warning(f"Failed to extract score from line: '{line}', error: {str(e)}")
        
        if score is None:
            logger.warning(f"Could not extract score from response. Ranking keyword '{ranking_keyword}' not found.")
        
        logger.info(f"Evaluation completed successfully with provider: {request.provider}, model: {request.model}")
        
        return EvaluationResponse(
            result=result,
            score=score,
            provider=request.provider,
            model=request.model
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions with logging
        logger.error(f"HTTP error in evaluation: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        # Handle other exceptions
        logger.exception(f"Evaluation failed with unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        ) 