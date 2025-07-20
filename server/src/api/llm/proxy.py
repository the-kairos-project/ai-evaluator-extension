"""LLM proxy endpoints for OpenAI and Anthropic."""

from typing import Dict, Any, Optional, List
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.auth import get_current_active_user, User
from src.config.settings import settings
from src.api.llm.prompt_system import (
    PromptTemplate, PromptVariables, PromptConfig, 
    build_prompt, get_template, ACADEMIC_TEMPLATE
)

# Create router
router = APIRouter(prefix="/llm", tags=["llm"])


class Message(BaseModel):
    """Message model for chat completion."""
    
    role: str
    content: str


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
    # Prepare request payload
    payload = {
        "model": request.model,
        "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
        "max_tokens": request.max_tokens,
    }
    
    # Add optional parameters if provided
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    if request.frequency_penalty is not None:
        payload["frequency_penalty"] = request.frequency_penalty
    if request.presence_penalty is not None:
        payload["presence_penalty"] = request.presence_penalty
    if request.stop:
        payload["stop"] = request.stop
    
    # Make request to OpenAI API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {request.api_key}",
                    "Content-Type": "application/json",
                },
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Return response
            return response.json()
            
        except httpx.HTTPStatusError as e:
            # Forward OpenAI error response
            error_info = e.response.json() if e.response.headers.get("content-type") == "application/json" else {"error": str(e)}
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"OpenAI API error: {error_info}"
            )
        except httpx.RequestError as e:
            # Network-related errors
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error communicating with OpenAI API: {str(e)}"
            )
        except Exception as e:
            # Unexpected errors
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
    # Check if the last message is a system message
    messages = request.messages
    last_message_is_system = len(messages) > 0 and messages[-1].role == "system"
    
    # Prepare request payload
    payload = {
        "model": request.model,
        "max_tokens": request.max_tokens,
    }
    
    # Handle system message specially
    if last_message_is_system:
        payload["messages"] = [{"role": msg.role, "content": msg.content} for msg in messages[:-1]]
        payload["system"] = messages[-1].content
    else:
        payload["messages"] = [{"role": msg.role, "content": msg.content} for msg in messages]
    
    # Add optional parameters if provided
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    if request.stop_sequences:
        payload["stop_sequences"] = request.stop_sequences
    
    # Make request to Anthropic API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": request.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                    "anthropic-dangerous-direct-browser-access": "true",
                },
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Return response
            return response.json()
            
        except httpx.HTTPStatusError as e:
            # Forward Anthropic error response
            error_info = e.response.json() if e.response.headers.get("content-type") == "application/json" else {"error": str(e)}
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Anthropic API error: {error_info}"
            )
        except httpx.RequestError as e:
            # Network-related errors
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error communicating with Anthropic API: {str(e)}"
            )
        except Exception as e:
            # Unexpected errors
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
    try:
        # Get the template (custom or from library)
        template = request.custom_template if request.custom_template else get_template(request.template_id)
        
        # Create variables for template substitution
        variables = PromptVariables(
            criteria_string=request.criteria_string,
            ranking_keyword=request.ranking_keyword or template.ranking_keyword,
            additional_instructions=request.additional_instructions or ""
        )
        
        # Build the prompt
        config = PromptConfig(template=template, variables=variables)
        messages = build_prompt(request.applicant_data, config)
        
        # Get the ranking keyword for score extraction
        ranking_keyword = variables.ranking_keyword or template.ranking_keyword
        
        # Call the appropriate provider
        if request.provider == "openai":
            # Create OpenAI request
            openai_request = OpenAIRequest(
                api_key=request.api_key,
                model=request.model,
                messages=[Message(role=msg["role"], content=msg["content"]) for msg in messages],
                max_tokens=500,
                temperature=0.2  # Lower temperature for more consistent evaluations
            )
            
            # Call OpenAI endpoint
            response = await proxy_openai(openai_request, current_user)
            result = response["choices"][0]["message"]["content"]
            
        elif request.provider == "anthropic":
            # Create Anthropic request
            anthropic_request = AnthropicRequest(
                api_key=request.api_key,
                model=request.model,
                messages=[Message(role=msg["role"], content=msg["content"]) for msg in messages],
                max_tokens=500,
                temperature=0.2  # Lower temperature for more consistent evaluations
            )
            
            # Call Anthropic endpoint
            response = await proxy_anthropic(anthropic_request, current_user)
            result = response["content"][0]["text"]
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}"
            )
        
        # Extract score from result
        score = None
        for line in result.split("\n"):
            if ranking_keyword in line:
                try:
                    # Find the score after the ranking keyword
                    score_part = line.split(f"{ranking_keyword} =")[1].strip()
                    # Extract the first number
                    score = int(''.join(filter(str.isdigit, score_part[:2])))
                    break
                except (IndexError, ValueError):
                    pass
        
        return EvaluationResponse(
            result=result,
            score=score,
            provider=request.provider,
            model=request.model
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle other exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        ) 