"""
Router for LLM proxy endpoints.

This module defines the FastAPI router for OpenAI and Anthropic proxy endpoints,
as well as the evaluation endpoint.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.auth import get_current_active_user, User
from src.api.llm.providers import ProviderFactory
from src.core.plugin_system.plugin_manager import PluginManager

from .models import OpenAIRequest, AnthropicRequest, EvaluationRequest, EvaluationResponse
from .enrichment import format_enrichment_data
from .plugins import process_linkedin_enrichment, process_pdf_enrichment
from .evaluation import build_evaluation_prompt, extract_score, extract_multi_axis_scores

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/openai", status_code=status.HTTP_200_OK)
async def proxy_openai(
    request: OpenAIRequest, 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Proxy requests to OpenAI API.
    
    Args:
        request: OpenAI request
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: OpenAI API response
    """
    try:
        from src.config.settings import settings
        # Use OpenAI-specific timeout if available, otherwise use general LLM timeout
        timeout = settings.openai_timeout if settings.openai_timeout else settings.llm_timeout
        provider = ProviderFactory.get_provider("openai", timeout=float(timeout))
        
        payload = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens
        }
        
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.stop is not None:
            payload["stop"] = request.stop
        
        response = await provider.generate(payload, api_key=request.api_key)
        
        return response
        
    except Exception as e:
        logger.error(f"OpenAI proxy error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI proxy error: {str(e)}"
        )


@router.post("/anthropic", status_code=status.HTTP_200_OK)
async def proxy_anthropic(
    request: AnthropicRequest, 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Proxy requests to Anthropic API.
    
    Args:
        request: Anthropic request
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: Anthropic API response
    """
    try:
        from src.config.settings import settings
        # Use general LLM timeout for Anthropic (no specific anthropic_timeout in settings)
        timeout = settings.llm_timeout
        provider = ProviderFactory.get_provider("anthropic", timeout=float(timeout))
        
        payload = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens
        }
        
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences is not None:
            payload["stop_sequences"] = request.stop_sequences
        
        response = await provider.generate(payload, api_key=request.api_key)
        
        return response
        
    except Exception as e:
        logger.error(f"Anthropic proxy error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anthropic proxy error: {str(e)}"
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
    
    enrichment_data = None
    enrichment_log = []
    linkedin_data_json = None
    pdf_data_json = None
    
    if request.use_plugin and request.source_url:
        logger.info(f"Plugin enrichment requested for URL: {request.source_url}")
        enrichment_log.append(f"Enrichment requested for URL: {request.source_url}")
        
        plugin_manager = None
        try:
            plugin_manager = PluginManager()
            logger.info("Initializing plugin manager")
            await plugin_manager.initialize()
            logger.info("Plugin manager initialized")
            
            available_plugins = plugin_manager.available_plugins
            loaded_plugins = plugin_manager.loaded_plugins
            logger.info(f"Available plugins: {available_plugins}")
            logger.info(f"Loaded plugins: {list(loaded_plugins.keys())}")
            enrichment_log.append(f"Available plugins: {available_plugins}")
            
            pdf_url = None
            if request.pdf_url:
                logger.info(f"Found PDF URL in request.pdf_url: {request.pdf_url}")
                enrichment_log.append(f"Found PDF URL in request: {request.pdf_url}")
                pdf_url = request.pdf_url
            # Fallback: check if source_url is a PDF when not LinkedIn
            elif "[object Object]" in request.applicant_data and "linkedin.com" not in request.source_url and request.source_url:
                logger.info(f"Using source_url as PDF URL: {request.source_url}")
                enrichment_log.append(f"Using source_url as PDF URL: {request.source_url}")
                pdf_url = request.source_url
                
            # Process PDF if URL is available (regardless of extension - will verify content type when downloading)
            if pdf_url and isinstance(pdf_url, str):
                pdf_enrichment_data, pdf_data_json = await process_pdf_enrichment(
                    plugin_manager, pdf_url, request.provider, request.model, enrichment_log
                )
            
            linkedin_enrichment_data = None
            if "linkedin.com" in request.source_url:
                enrichment_data, linkedin_data_json = await process_linkedin_enrichment(
                    plugin_manager, request.source_url, enrichment_log
                )
                linkedin_enrichment_data = enrichment_data
                
            # Process PDF URL - either from pdf_url field or source_url if it's a PDF
            pdf_enrichment_data = None
            
            if request.pdf_url and isinstance(request.pdf_url, str):
                enrichment_log.append(f"Processing PDF URL from pdf_url field: {request.pdf_url}")
                pdf_enrichment_data, pdf_data_json = await process_pdf_enrichment(
                    plugin_manager, request.pdf_url, request.provider, request.model, enrichment_log
                )
            elif request.source_url and "linkedin.com" not in request.source_url:
                pdf_enrichment_data, pdf_data_json = await process_pdf_enrichment(
                    plugin_manager, request.source_url, request.provider, request.model, enrichment_log
                )
                
            if linkedin_enrichment_data and pdf_enrichment_data:
                # If we have both LinkedIn and PDF data, merge them
                # Create a combined enrichment data structure
                combined_data = {
                    "type": "combined",
                    "data": {
                        "linkedin": linkedin_enrichment_data.get("data", {}),
                        "pdf": pdf_enrichment_data.get("data", {})
                    }
                }
                enrichment_data = combined_data
            elif pdf_enrichment_data:
                enrichment_data = pdf_enrichment_data
                
            else:
                warning_msg = f"Unrecognized source URL format: {request.source_url}"
                logger.warning(warning_msg)
                enrichment_log.append(warning_msg)
                
        except Exception as exc:
            error_msg = f"Plugin enrichment failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)  # Include stack trace
            logger.debug(f"Plugin enrichment exception type: {type(exc).__name__}")
            enrichment_log.append(error_msg)
        finally:
            # Always clean up the plugin manager to avoid resource leaks
            if plugin_manager:
                logger.debug("Shutting down plugin manager")
                await plugin_manager.shutdown()
                logger.debug("Plugin manager shutdown complete")
    
    try:
        enrichment_text = None
        if enrichment_data:
            enrichment_text = format_enrichment_data(enrichment_data)
            enrichment_log.append("Formatted enrichment data for prompt")
        enhanced_applicant_data = request.applicant_data
        if enrichment_text:
            # For both providers, add the enrichment data directly to the applicant data
            # This ensures it's processed as part of the initial context
            enhanced_applicant_data = f"{request.applicant_data}\n\n### CANDIDATE ENRICHMENT DATA:\n{enrichment_text}"
            enrichment_log.append("Added enrichment data to applicant data")
            
        # If using multi-axis, force the SPAR template and clean up parameters
        template_id = request.template_id
        criteria_string = request.criteria_string
        ranking_keyword = request.ranking_keyword
        additional_instructions = request.additional_instructions
        
        if request.use_multi_axis:
            template_id = "multi_axis_spar"
            
            if not criteria_string or criteria_string.strip() == "":
                criteria_string = "Evaluate the candidate for the SPAR research program."
                
            ranking_keyword = None
            
            if not additional_instructions or additional_instructions.strip() == "":
                additional_instructions = "Return a score from 1-5 for each of the evaluation axes."
        
        messages, ranking_keywords = await build_evaluation_prompt(
            enhanced_applicant_data,
            criteria_string,
            template_id,
            ranking_keyword,
            additional_instructions,
            request.custom_template,
            use_multi_axis=request.use_multi_axis
        )
        
        from src.config.settings import settings
        
        try:
            # Determine timeout based on provider
            if request.provider == "openai":
                timeout = settings.openai_timeout if settings.openai_timeout else settings.llm_timeout
            else:
                # For anthropic and other providers, use general LLM timeout
                timeout = settings.llm_timeout
            
            provider = ProviderFactory.get_provider(request.provider, timeout=float(timeout))
            logger.debug(f"Using provider: {provider.name} with timeout: {timeout}s")
        except ValueError:
            logger.error(f"Invalid provider in evaluation request: {request.provider}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {request.provider}"
            )
        
        max_tokens = 4096  # Default fallback
        if request.provider == "openai":
            max_tokens = settings.openai_max_tokens
        elif request.provider == "anthropic":
            max_tokens = settings.anthropic_max_tokens
        elif settings.llm_max_tokens is not None:
            max_tokens = settings.llm_max_tokens
            
        
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": 0.2,  # Use a lower temperature for more consistent results
            "max_tokens": max_tokens  # Use max_tokens from environment settings
        }

        logger.info(f"Calling {request.provider} API for evaluation")
        response = await provider.generate(payload, api_key=request.api_key)
        
        if request.provider == "openai":
            completion = response["choices"][0]["message"]["content"]
        else:  # anthropic
            completion = response["content"][0]["text"]
        
        scores = None
        score = None
        
        if request.use_multi_axis:
            # Check for section headers and score patterns for each axis
            import re
            
            for axis_name in ranking_keywords.keys():
                section_headers = [
                    f"## {axis_name}",
                    f"**{axis_name}**",
                    f"{axis_name}:",
                    f"{axis_name} Rating"
                ]
                
                patterns = [
                    rf"{axis_name}\s*[:=]\s*([1-5])",
                    rf"{ranking_keywords[axis_name]}\s*[:=]\s*([1-5])",  # GENERAL_PROMISE_RATING: 4
                    rf"{ranking_keywords[axis_name]}\s*=\s*([1-5])",  # GENERAL_PROMISE_RATING = 4
                ]
                
                header_found = False
                for header in section_headers:
                    if header in completion:
                        header_found = True
                        break
                
                if not header_found:
                    logger.debug(f"Missing section header for axis: {axis_name}")
                
                pattern_found = False
                for pattern in patterns:
                    match = re.search(pattern, completion, re.IGNORECASE | re.DOTALL)
                    if match:
                        pattern_found = True
                        break
                
                if not pattern_found:
                    logger.debug(f"No score pattern found for axis: {axis_name}")
            
            # Extract multiple scores for each axis
            scores = extract_multi_axis_scores(completion, ranking_keywords)
            logger.info(f"Extracted multi-axis scores: {[f'{s.name}: {s.score}' for s in scores]}")
            
            extracted_count = sum(1 for s in scores if s.score is not None)
            
            if scores and scores[0].score is not None:
                score = scores[0].score
            if extracted_count == 0:
                completion += "\n\n[WARNING] No multi-axis scores could be extracted from the LLM response. Please check the prompt format and extraction logic."
        else:
            score = extract_score(completion, ranking_keywords)
            logger.info(f"Extracted score: {score}")
        
        if request.use_multi_axis and scores and len(scores) > 0:
            multi_axis_data = []
            for axis_score in scores:
                if axis_score.score is not None:
                    multi_axis_data.append(f"{axis_score.name}: {axis_score.score}")
                else:
                    multi_axis_data.append(f"{axis_score.name}: Not found")
            multi_axis_text = "\n".join(multi_axis_data)
            completion += f"\n\n[MULTI_AXIS_SCORES]\n{multi_axis_text}\n[END_MULTI_AXIS_SCORES]"
            
        if enrichment_log:
            completion += "\n\n[ENRICHMENT LOG]\n" + "\n".join(enrichment_log) + "\n[END ENRICHMENT LOG]"
        
        if linkedin_data_json:
            completion += f"\n\n[LINKEDIN_DATA]\n{linkedin_data_json}\n[END_LINKEDIN_DATA]"
            
        if pdf_data_json:
            completion += f"\n\n[PDF_RESUME_DATA]\n{pdf_data_json}\n[END_PDF_RESUME_DATA]"
        
        return EvaluationResponse(
            result=completion,
            score=score,
            scores=scores if request.use_multi_axis else None,
            provider=request.provider,
            model=request.model
        )
        
    except Exception as exc:
        logger.error(f"Evaluation error: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation error: {str(exc)}"
        )