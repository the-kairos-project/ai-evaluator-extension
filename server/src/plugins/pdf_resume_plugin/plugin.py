"""
PDF Resume Parser Plugin implementation.

This module provides the main plugin class for the PDF resume parser.
"""

from typing import Any, Dict, Optional
from src.utils.logging import get_structured_logger

from src.core.plugin_system.plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse

from .models import ResumeData
from .extractor import download_pdf, extract_text_from_pdf
from .parser import parse_resume_text
from .llm_fallback import parse_with_llm

logger = get_structured_logger(__name__)


class PDFResumePlugin(Plugin):
    """Plugin for parsing PDF resumes and extracting structured data."""
    
    def __init__(self) -> None:
        """Initialize the PDF Resume Parser plugin."""
        super().__init__()
        self._metadata = PluginMetadata(
            name="pdf_resume_parser",
            version="1.0.0",
            description="Extracts text and structured data from PDF resumes",
            author="MCP Team",
            capabilities=["pdf_parsing", "resume_parsing", "document_extraction"],
            required_params={
                "pdf_url": "URL to the PDF resume to parse"
            },
            optional_params={
                "use_llm_fallback": "Whether to use LLM fallback if direct extraction fails (boolean, default: True)",
                "llm_provider": "LLM provider to use for fallback (string, default: 'anthropic')",
                "llm_model": "LLM model to use for fallback (string, default: 'claude-3-5-sonnet-20241022')"
            },
            examples=[
                {
                    "query": "Parse resume from URL",
                    "parameters": {"pdf_url": "https://example.com/resume.pdf"}
                },
                {
                    "query": "Parse resume without LLM fallback",
                    "parameters": {"pdf_url": "https://example.com/resume.pdf", "use_llm_fallback": False}
                }
            ]
        )
        self._initialized = False
        self._llm_provider = None
        self._llm_model = None
        
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin.
        
        Args:
            config: Optional configuration
        """
        logger.info("Initializing PDF Resume Parser plugin", config=config)
        
        # Set default LLM provider and model
        self._llm_provider = "anthropic"
        self._llm_model = "claude-3-5-sonnet-20241022"
        
        # Override with config if provided
        if config:
            if "llm_provider" in config:
                self._llm_provider = config["llm_provider"]
            if "llm_model" in config:
                self._llm_model = config["llm_model"]
        
        self._initialized = True
        logger.info("PDF Resume Parser plugin initialized", 
                   llm_provider=self._llm_provider, 
                   llm_model=self._llm_model)
    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        """Execute the PDF resume parsing functionality.
        
        Args:
            request: The plugin request
            
        Returns:
            PluginResponse: The parsed resume data
        """
        try:
            # Extract parameters
            pdf_url = request.parameters.get("pdf_url")
            use_llm_fallback = request.parameters.get("use_llm_fallback", True)
            llm_provider = request.parameters.get("llm_provider", self._llm_provider)
            llm_model = request.parameters.get("llm_model", self._llm_model)
            
            logger.info("PDF Resume plugin execution started", 
                       pdf_url=pdf_url, 
                       use_llm_fallback=use_llm_fallback,
                       llm_provider=llm_provider,
                       llm_model=llm_model)
            
            if not pdf_url:
                logger.error("Missing required parameter: pdf_url")
                return PluginResponse(
                    request_id=request.request_id,
                    status="error",
                    error="Missing required parameter: pdf_url"
                )
            
            # Download the PDF
            logger.info("Downloading PDF", url=pdf_url)
            pdf_content = await download_pdf(pdf_url)
            
            # Extract text from PDF
            logger.info("Extracting text from PDF")
            pdf_text = extract_text_from_pdf(pdf_content)
            logger.info("Text extraction complete", text_length=len(pdf_text))
            
            # Parse resume data using direct extraction
            logger.info("Parsing resume data using direct extraction")
            resume_data = parse_resume_text(pdf_text)
            logger.info("Direct extraction results", 
                      personal_info=resume_data.personal_info.name is not None,
                      education_entries=len(resume_data.education),
                      experience_entries=len(resume_data.experience),
                      skills_found=len(resume_data.skills))
            
            # Check if we need LLM fallback
            needs_fallback = needs_llm_fallback(resume_data)
            if use_llm_fallback and needs_fallback:
                logger.info("Direct extraction incomplete, using LLM fallback EXCLUSIVELY", 
                           provider=llm_provider, 
                           model=llm_model)
                # Create empty resume data for LLM parsing - don't pass the incomplete data
                # This ensures we don't mix the two extraction methods
                empty_resume_data = ResumeData()
                resume_data = await parse_with_llm(pdf_text, empty_resume_data, llm_provider, llm_model)
                logger.info("LLM-only parsing completed")
            elif needs_fallback and not use_llm_fallback:
                logger.warning("Direct extraction incomplete and LLM fallback disabled", 
                               missing_sections={
                                   "personal_info": not bool(resume_data.personal_info.name),
                                   "education": len(resume_data.education) == 0,
                                   "experience": len(resume_data.experience) == 0,
                                   "skills": len(resume_data.skills) == 0,
                               })
            
            logger.info("PDF resume parsing complete", 
                       text_length=len(pdf_text) if pdf_text else 0,
                       data_fields=list(resume_data.dict().keys()) if resume_data else [],
                       personal_info=resume_data.personal_info.name or 'Not found',
                       education_entries=len(resume_data.education),
                       experience_entries=len(resume_data.experience),
                       skills_found=len(resume_data.skills),
                       used_llm_fallback=use_llm_fallback and needs_fallback)
            
            response_data = {
                "parsed_resume": resume_data.dict(),
                "text_length": len(pdf_text),
                "source_url": pdf_url
            }
            
            logger.debug(f"Returning response with {len(str(response_data))} characters of data")
            
            return PluginResponse(
                request_id=request.request_id,
                status="success",
                data=response_data,
                metadata={
                    "plugin": "pdf_resume_parser",
                    "version": self._metadata.version,
                    "used_llm_fallback": use_llm_fallback and needs_fallback
                }
            )
            
        except Exception as e:
            logger.error("PDF resume parsing failed", error=str(e), exc_info=True)
            return PluginResponse(
                request_id=request.request_id,
                status="error",
                error=f"PDF resume parsing failed: {str(e)}"
            )
    
    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info("Shutting down PDF Resume Parser plugin")
        self._initialized = False
    
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata.
        
        Returns:
            PluginMetadata: The plugin's metadata
        """
        return self._metadata


def needs_llm_fallback(resume_data: ResumeData) -> bool:
    """Check if LLM fallback is needed based on the quality of direct extraction.
    
    Args:
        resume_data: Resume data from direct extraction
        
    Returns:
        bool: True if LLM fallback is needed
    """
    # Check if key sections are missing or incomplete
    
    # Check personal info
    if not resume_data.personal_info.name:
        return True
    
    # Check education
    if not resume_data.education:
        return True
    
    # Check experience
    if not resume_data.experience:
        return True
    
    # Check skills
    if not resume_data.skills:
        return True
    
    # Check if experience entries have missing titles or responsibilities
    for exp in resume_data.experience:
        if not exp.title or not exp.responsibilities:
            return True
    
    # If we have at least basic info in all key sections, no need for fallback
    return False