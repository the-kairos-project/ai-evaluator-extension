"""
PDF text extraction functionality.

This module handles downloading PDFs and extracting text using pdfminer.six.
"""

import io
import re
import requests
from typing import Optional

from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


async def download_pdf(url: str) -> bytes:
    """Download PDF from URL.
    
    Args:
        url: URL of the PDF to download
        
    Returns:
        bytes: PDF content
        
    Raises:
        Exception: If download fails
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        logger.info(f"Downloading PDF from URL: {url}")
        response = requests.get(url, headers=headers, timeout=60)  # Increase timeout for large files
        response.raise_for_status()
        
        # Check content type and URL patterns
        content_type = response.headers.get("Content-Type", "")
        
        # Handle different cases:
        # 1. Content-Type is PDF
        # 2. URL ends with .pdf
        # 3. Airtable URL that contains PDF content (special case)
        is_pdf = False
        
        if "application/pdf" in content_type.lower():
            logger.debug(f"Content-Type confirms this is a PDF: {content_type}")
            is_pdf = True
        elif url.lower().endswith(".pdf"):
            logger.debug("URL ends with .pdf extension")
            is_pdf = True
        elif "airtableusercontent.com" in url and any(ext in response.headers.get("Content-Disposition", "").lower() for ext in [".pdf", "filename=", "filename*="]):
            logger.debug("Airtable URL with PDF content detected via Content-Disposition header")
            is_pdf = True
        elif "airtableusercontent.com" in url and len(response.content) > 1000:
            # For Airtable URLs, check if the content looks like a PDF (starts with %PDF-)
            first_bytes = response.content[:10].decode('utf-8', errors='ignore')
            if "%PDF-" in first_bytes:
                logger.debug("Content starts with %PDF- magic bytes - confirmed PDF content")
                is_pdf = True
            else:
                logger.debug(f"First bytes of content: {first_bytes}")
        
        if not is_pdf:
            logger.warning(f"Content may not be a PDF. Content-Type: {content_type}", 
                          url=url, 
                          content_type=content_type)
        
        return response.content
    except Exception as e:
        logger.error("Failed to download PDF", url=url, error=str(e))
        raise Exception(f"Failed to download PDF from {url}: {str(e)}")


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF content.
    
    Args:
        pdf_content: PDF content as bytes
        
    Returns:
        str: Extracted text
        
    Raises:
        Exception: If extraction fails
    """
    try:
        # First check if content looks like a PDF (should start with %PDF-)
        first_bytes = pdf_content[:10].decode('utf-8', errors='ignore')
        if "%PDF-" not in first_bytes:
            logger.warning(f"Content doesn't appear to be a PDF. First bytes: {first_bytes}")
            if len(pdf_content) < 200:
                logger.debug(f"Content (short): {pdf_content.decode('utf-8', errors='ignore')}")
            # Continue anyway - maybe pdfminer can still extract something
        
        # Create a file-like object from bytes
        pdf_file = io.BytesIO(pdf_content)
        
        # Extract text with pdfminer.six
        logger.info("Extracting text with pdfminer.six")
        laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            all_texts=True
        )
        
        text = extract_text(pdf_file, laparams=laparams)
        
        # Check if we got any text
        if not text or len(text.strip()) < 10:
            logger.warning(f"Extracted very little text: {len(text)} chars")
        else:
            logger.info(f"Successfully extracted {len(text)} characters")
        
        # Clean up text
        text = clean_text(text)
        
        logger.info("Text extraction successful", text_length=len(text))
        return text
    except Exception as e:
        logger.error("Failed to extract text from PDF", error=str(e))
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def clean_text(text: str) -> str:
    """Clean extracted text.
    
    Args:
        text: Raw extracted text
        
    Returns:
        str: Cleaned text
    """
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove non-printable characters
    text = ''.join(c for c in text if c.isprintable() or c == '\n')
    
    return text.strip()


def extract_section(text: str, section_name: str, next_section_names: Optional[list] = None) -> Optional[str]:
    """Extract a specific section from the text.
    
    Args:
        text: Full text
        section_name: Name of the section to extract
        next_section_names: Names of sections that might follow
        
    Returns:
        Optional[str]: Extracted section or None if not found
    """
    if next_section_names is None:
        next_section_names = ["education", "experience", "skills", "projects", "languages"]
    
    # Create regex pattern for section heading
    section_pattern = re.compile(
        r'(?:^|\n)(?:\s*)({}|{})(?:\s*:?\s*)(?:\n|$)'.format(
            section_name, section_name.upper()
        ), 
        re.IGNORECASE
    )
    
    # Find the start of the section
    match = section_pattern.search(text)
    if not match:
        return None
    
    section_start = match.end()
    
    # Find the end of the section (next section heading)
    section_end = len(text)
    
    # Create regex pattern for next section headings
    for next_section in next_section_names:
        if next_section.lower() == section_name.lower():
            continue
            
        next_pattern = re.compile(
            r'(?:^|\n)(?:\s*)({}|{})(?:\s*:?\s*)(?:\n|$)'.format(
                next_section, next_section.upper()
            ), 
            re.IGNORECASE
        )
        
        next_match = next_pattern.search(text, section_start)
        if next_match and next_match.start() < section_end:
            section_end = next_match.start()
    
    # Extract the section
    section_text = text[section_start:section_end].strip()
    return section_text