"""
Plugin handling for LLM evaluation.

This module provides functions for working with plugins in the evaluation process,
including LinkedIn and PDF resume enrichment.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from src.core.plugin_system.plugin_manager import PluginManager
from src.core.plugin_system.plugin_interface import PluginRequest

logger = logging.getLogger(__name__)


async def process_linkedin_enrichment(
    plugin_manager: PluginManager,
    source_url: str,
    enrichment_log: List[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Process LinkedIn enrichment.
    
    Args:
        plugin_manager: Plugin manager instance
        source_url: LinkedIn profile URL
        enrichment_log: List to append log messages to
        
    Returns:
        Tuple of (enrichment_data, data_json)
    """
    logger.info(f"Detected LinkedIn profile URL: {source_url}")
    enrichment_log.append(f"Detected LinkedIn profile URL: {source_url}")
    
    try:
        # Load LinkedIn plugin
        logger.info("Attempting to load LinkedIn plugin")
        
        plugin_name = "linkedin_external"  # Name from LinkedInExternalPlugin.get_metadata()
        
        try:
            plugin = await plugin_manager.load_plugin(plugin_name)
            logger.info("LinkedIn plugin loaded successfully")
            logger.debug(f"Plugin type: {type(plugin)}")
            logger.debug(f"Plugin initialized: {getattr(plugin, '_initialized', False)}")
            enrichment_log.append("LinkedIn plugin loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load LinkedIn plugin: {str(e)}"
            logger.error(error_msg, exc_info=True)
            enrichment_log.append(error_msg)
            raise
        
        # Parse URL to get username if full URL provided
        linkedin_username = source_url
        if "linkedin.com/in/" in source_url:
            linkedin_username = source_url.split("linkedin.com/in/")[1].split("/")[0]
            logger.info(f"Extracted LinkedIn username: {linkedin_username}")
            logger.debug(f"Username extraction: {source_url} -> {linkedin_username}")
            enrichment_log.append(f"Extracted LinkedIn username: {linkedin_username}")
        
        # Create plugin request
        request_id = f"req_{datetime.utcnow().timestamp()}"
        logger.debug(f"Generated request ID: {request_id}")
        plugin_request = PluginRequest(
            request_id=request_id,
            action="get_person_profile",
            parameters={"linkedin_username": linkedin_username}
        )
        
        # Execute plugin
        logger.info(f"Executing LinkedIn plugin for username: {linkedin_username}")
        enrichment_log.append(f"Executing LinkedIn plugin for username: {linkedin_username}")
        
        # Log plugin request details
        logger.info(f"Plugin request: action={plugin_request.action}, parameters={plugin_request.parameters}")
        logger.debug(f"Full plugin request: {plugin_request}")
        
        try:
            start_time = datetime.utcnow()
            logger.debug(f"Plugin execution started at: {start_time}")
            response = await plugin.execute(plugin_request)
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            logger.debug(f"Plugin execution completed in {execution_time:.2f} seconds")
            
            # Log plugin response details
            logger.info(f"Plugin response: status={response.status}, error={response.error if response.error else 'None'}")
            logger.info(f"Plugin response data type: {type(response.data)}")
            logger.debug(f"Plugin response metadata: {response.metadata}")
            
            if response.status == "success" and response.data:
                logger.info("LinkedIn data received successfully")
                
                enrichment_data = {
                    "type": "linkedin",
                    "data": response.data
                }
                
                # Store LinkedIn data in JSON format for including in result
                try:
                    linkedin_data_json = json.dumps(response.data, indent=2)
                except Exception as e:
                    linkedin_data_json = None
                    
                logger.info("LinkedIn enrichment successful")
                logger.debug(f"LinkedIn data JSON length: {len(linkedin_data_json) if linkedin_data_json else 0}")
                logger.info(f"LinkedIn data: {linkedin_data_json[:100]}..." if linkedin_data_json else "None")  # Log first 100 chars
                enrichment_log.append("LinkedIn enrichment successful")
                enrichment_log.append(f"Retrieved profile data: {len(str(response.data))} characters")
                
                return enrichment_data, linkedin_data_json
            else:
                # Check for authentication errors
                if response.data and isinstance(response.data, dict) and response.data.get("error") == "login_timeout":
                    error_msg = f"LinkedIn authentication failed: {response.data.get('message', 'Cookie may be expired')}"
                    logger.error(error_msg)
                    logger.debug(f"Full error data: {response.data}")
                    enrichment_log.append(error_msg)
                    enrichment_log.append("IMPORTANT: Update the LINKEDIN_COOKIE environment variable with a fresh cookie")
                else:
                    error_msg = f"LinkedIn plugin failed: {response.error or str(response.data)}"
                    logger.error(error_msg)
                    logger.debug(f"Response status: {response.status}, Error: {response.error}")
                    enrichment_log.append(error_msg)
        except Exception as e:
            error_msg = f"LinkedIn plugin execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            logger.debug(f"Plugin execution exception type: {type(e).__name__}")
            enrichment_log.append(error_msg)
            
    except Exception as e:
        error_msg = f"LinkedIn plugin error: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Include stack trace
        logger.debug(f"Plugin loading exception type: {type(e).__name__}")
        enrichment_log.append(error_msg)
    
    return None, None


async def process_pdf_enrichment(
    plugin_manager: PluginManager,
    source_url: str,
    provider: str,
    model: str,
    enrichment_log: List[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Process PDF resume enrichment.
    
    Args:
        plugin_manager: Plugin manager instance
        source_url: PDF URL
        provider: LLM provider to use for fallback
        model: LLM model to use for fallback
        enrichment_log: List to append log messages to
        
    Returns:
        Tuple of (enrichment_data, data_json)
    """
    logger.info(f"Detected document URL - Using PDF resume parser: {source_url}")
    enrichment_log.append(f"Detected document URL - Using PDF resume parser: {source_url}")
    
    # Log available plugins
    
    try:
        # Load PDF resume plugin - use the correct name from the metadata
        logger.info("Attempting to load PDF Resume plugin")
        
        # Use the standard plugin name 
        plugin_name = "pdf_resume_parser"
        
        try:
            plugin = await plugin_manager.load_plugin(plugin_name)
            logger.info("PDF Resume plugin loaded successfully")
            enrichment_log.append("PDF Resume plugin loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load PDF plugin: {str(e)}"
            logger.error(error_msg)
            enrichment_log.append(error_msg)
            raise
        
        # Create plugin request
        request_id = f"req_{datetime.utcnow().timestamp()}"
        plugin_request = PluginRequest(
            request_id=request_id,
            action="parse_resume",
            parameters={
                "pdf_url": source_url,
                "use_llm_fallback": True,
                "llm_provider": provider,
                "llm_model": model
            }
        )
        
        # Execute plugin
        logger.info(f"Executing PDF Resume plugin for URL: {source_url}")
        enrichment_log.append(f"Executing PDF Resume plugin for URL: {source_url}")
        
        try:
            start_time = datetime.utcnow()
            response = await plugin.execute(plugin_request)
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            logger.debug(f"Plugin execution completed in {execution_time:.2f} seconds")
            
            if response.status == "success" and response.data:
                logger.info("PDF resume data received successfully")
                
                # Store the parsed resume data
                pdf_data = response.data
                enrichment_data = {
                    "type": "pdf",
                    "data": pdf_data
                }
                
                # Store PDF data in JSON format for including in result
                try:
                    pdf_data_json = json.dumps(pdf_data, indent=2)
                    logger.info(f"PDF data JSON successfully created, length: {len(pdf_data_json)}")
                except Exception as e:
                    logger.error(f"Error converting PDF data to JSON: {str(e)}")
                    pdf_data_json = None
                    
                logger.info("PDF resume enrichment successful")
                enrichment_log.append("PDF resume enrichment successful")
                enrichment_log.append(f"Retrieved resume data: {len(str(response.data))} characters")
                
                return enrichment_data, pdf_data_json
            else:
                error_msg = f"PDF resume plugin failed: {response.error or str(response.data)}"
                logger.error(error_msg)
                enrichment_log.append(error_msg)
        except Exception as e:
            error_msg = f"PDF resume plugin execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            enrichment_log.append(error_msg)
            
    except Exception as e:
        error_msg = f"PDF resume plugin error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        enrichment_log.append(error_msg)
    
    return None, None