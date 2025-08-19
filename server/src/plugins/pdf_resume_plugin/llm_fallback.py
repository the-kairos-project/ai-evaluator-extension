"""
LLM fallback for PDF resume parsing.

This module provides LLM-based parsing when direct extraction fails.
"""

import json
import re

from src.utils.logging import get_structured_logger

from src.api.llm.providers import ProviderFactory
import unicodedata
from typing import Any, Dict

logger = get_structured_logger(__name__)


async def parse_with_llm(
    text: str, 
    direct_extraction_data: Dict[str, Any],
    provider_name: str,
    model_name: str
) -> Dict[str, Any]:
    """Use LLM to parse resume when direct extraction fails.
    
    Args:
        text: Raw text from PDF
        direct_extraction_data: Data from direct extraction (may be incomplete)
        provider_name: LLM provider to use
        model_name: LLM model to use
        
    Returns:
        Dict[str, Any]: Structured resume data from LLM
    """
    try:
        # Truncate text if too long
        max_text_length = 50000  # Adjust based on model context limits
        truncated_text = text[:max_text_length] if len(text) > max_text_length else text
        
        # Create prompt for LLM
        prompt = create_llm_prompt(truncated_text, direct_extraction_data)
        
        # Get LLM provider with appropriate timeout
        from src.config.settings import settings
        timeout = settings.llm_timeout  # Use general LLM timeout for PDF parsing
        provider = ProviderFactory.get_provider(provider_name, timeout=float(timeout))
        
        # Create request with proper message order and prefilling
        messages = [
            {"role": "system", "content": "You are an expert resume parser. Output ONLY valid JSON. No explanations, no text before or after the JSON."},
            {"role": "user", "content": prompt}
        ]
        
        # Add prefilling for Anthropic to force JSON output
        if provider_name == "anthropic":
            messages.append({"role": "assistant", "content": "{"})
        
        request = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2000,
        }
        
        # Call LLM
        logger.info("Calling LLM for resume parsing", provider=provider_name, model=model_name)
        # Supply provider API key explicitly (bug fix: missing API key caused fallback to fail)
        api_key = settings.get_llm_api_key(provider_name)
        response = await provider.generate(request, api_key=api_key)
        
        # Parse the response
        if provider_name == "openai":
            content = response["choices"][0]["message"]["content"]
        else:  # anthropic
            content = response["content"][0]["text"]
            # If we prefilled with "{", the response will start where we left off
            # So we need to prepend the "{" back
            if not content.strip().startswith("{"):
                content = "{" + content
            
        parsed_data = parse_llm_response(content)
        # Normalize parsed data for Unicode and minor unit fixes
        normalized = normalize_resume_data(text, parsed_data)
        
        # Merge with direct extraction data for any fields that might be missing
        merged_data = merge_resume_data(direct_extraction_data, normalized)
        
        logger.info("LLM parsing successful")
        return merged_data
        
    except Exception as e:
        logger.error("LLM fallback parsing failed", error=str(e))
        # Return the direct extraction data if LLM fails
        return direct_extraction_data


def create_llm_prompt(text: str, direct_extraction_data: Dict[str, Any]) -> str:
    """Create prompt for LLM resume parsing.
    
    Args:
        text: Raw text from PDF
        direct_extraction_data: Data from direct extraction (now empty by design)
        
    Returns:
        str: Prompt for LLM
    """
    prompt = f"""
Parse the following resume text into a structured JSON format that follows this exact schema:

```json
{{
  "personal_info": {{
    "name": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null"
  }},
  "education": [
    {{
      "institution": "string",
      "degree": "string or null",
      "period": "string or null",
      "details": "string or null"
    }}
  ],
  "experience": [
    {{
      "company": "string",
      "title": "string or null",
      "period": "string or null",
      "responsibilities": ["string"]
    }}
  ],
  "skills": ["string"],
  "projects": [
    {{
      "name": "string or null",
      "description": "string or null",
      "technologies": ["string"],
      "url": "string or null"
    }}
  ],
  "languages": [
    {{
      "language": "string",
      "proficiency": "string or null"
    }}
  ]
}}
```

STRICT REQUIREMENTS:
1. Output MUST be valid, parseable JSON. Return ONLY the JSON object with no additional text.
2. Preserve Unicode accents/diacritics exactly (UTF-8). Do NOT replace characters like á, é, í, ó, ú, ü, ñ, ç.
3. Periods must be extracted from the same section as company/title. Recognize and preserve Present/Currently (e.g., "May 2025 – Present"). Accept formats like "Jan. 2024 – Present", "July 2023 – Oct. 2023", or "2021–2023".
4. Retain symbols and units (%, $, k, M) exactly as written.
5. Include ONLY 2–3 most recent education entries, 3–4 most recent experience entries, and 5–10 key skills.
6. Keep responsibility descriptions very brief (1–2 sentences max).
7. Include ONLY information explicitly present in the text. If information is not present, use null (for scalars) or an empty array (for lists). Do NOT guess or infer.
8. Use only the keys defined in the schema above. Do not add extra keys.
9. LIMIT TOTAL OUTPUT to 1500 words maximum
10. Return ONLY the JSON object. No explanations, no additional text.

RESUME TEXT:
{text}
"""
    return prompt


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM response into structured data.
    
    Args:
        response_text: Text response from LLM
        
    Returns:
        Dict[str, Any]: Structured resume data
    """
    try:
        # First, try to extract JSON from code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try to find JSON object boundaries
            # Look for the first { and find its matching }
            start_idx = response_text.find('{')
            if start_idx == -1:
                raise ValueError("No JSON object found in response")
            
            # Find the matching closing brace
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(response_text)):
                if response_text[i] == '{':
                    brace_count += 1
                elif response_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count != 0:
                # If we can't find matching braces, try to parse the whole thing
                json_str = response_text.strip()
            else:
                json_str = response_text[start_idx:end_idx]
        
        # Clean up the JSON string
        json_str = json_str.strip()
        
        # Log a preview if parsing is about to fail
        if not json_str.startswith('{') or not json_str.endswith('}'):
            logger.warning("JSON extraction may fail", 
                          preview=json_str[:100] + "..." if len(json_str) > 100 else json_str)
        
        # Parse JSON
        parsed_data = json.loads(json_str)
        
        # Basic validation - just check for expected keys and non-empty content
        expected_keys = {"personal_info", "education", "experience", "skills", "projects", "languages"}
        missing_keys = expected_keys - set(parsed_data.keys())
        if missing_keys:
            logger.warning("Parsed JSON missing expected keys", missing_keys=list(missing_keys))
        
        # Check if we have meaningful content by measuring total data length
        def get_content_length(data):
            """Recursively calculate the total content length in the data structure."""
            if isinstance(data, str):
                return len(data.strip())
            elif isinstance(data, dict):
                return sum(get_content_length(v) for v in data.values() if v is not None)
            elif isinstance(data, list):
                return sum(get_content_length(item) for item in data)
            else:
                return 0
        
        total_content_length = get_content_length(parsed_data)
        
        # Also count non-empty fields
        non_empty_fields = 0
        if parsed_data.get("personal_info", {}).get("name"):
            non_empty_fields += 1
        if parsed_data.get("personal_info", {}).get("email"):
            non_empty_fields += 1
        non_empty_fields += len(parsed_data.get("education", []))
        non_empty_fields += len(parsed_data.get("experience", []))
        non_empty_fields += len(parsed_data.get("skills", []))
        non_empty_fields += len(parsed_data.get("projects", []))
        non_empty_fields += len(parsed_data.get("languages", []))
        
        # Fail if total content is too short or too few fields have data
        # A reasonable resume should have at least 100 chars of content and 3+ non-empty fields
        if total_content_length < 100 or non_empty_fields < 3:
            logger.error("Parsed JSON has insufficient content - treating as parsing failure",
                        content_length=total_content_length,
                        non_empty_fields=non_empty_fields)
            raise ValueError(f"LLM returned insufficient resume data (content_length={total_content_length}, fields={non_empty_fields})")
        
        # Return the raw parsed data - no Pydantic validation
        return parsed_data
            
    except json.JSONDecodeError as e:
        logger.error("JSON parsing failed", 
                    error=str(e),
                    response_preview=response_text[:200] + "..." if len(response_text) > 200 else response_text)
        # Return empty structure if parsing fails
        return {}
    except Exception as e:
        logger.error("Failed to parse LLM response", 
                    error=str(e),
                    error_type=type(e).__name__)
        # Return empty structure if parsing fails
        return {}


def merge_resume_data(direct_data: Dict[str, Any], llm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge direct extraction data with LLM data.
    
    Args:
        direct_data: Data from direct extraction (now always empty by design)
        llm_data: Data from LLM
        
    Returns:
        Dict[str, Any]: Parsed data from LLM
    """
    # Since we're now passing an empty ResumeData object by design,
    # we simply return the LLM data directly to avoid any mixing
    return llm_data


# ----------------------
# Normalization utilities
# ----------------------

def _normalize_string(value: str) -> str:
    if not isinstance(value, str):
        return value
    # Unicode normalization first
    normalized = unicodedata.normalize("NFC", value)
    # Fix spacing acute accent U+00B4 before vowels → precomposed accented vowels
    replacements = {
        "´a": "á", "´e": "é", "´i": "í", "´o": "ó", "´u": "ú",
        "´A": "Á", "´E": "É", "´I": "Í", "´O": "Ó", "´U": "Ú",
    }
    for seq, rep in replacements.items():
        normalized = normalized.replace(seq, rep)
    # Collapse excessive internal whitespace
    normalized = " ".join(normalized.split())
    return normalized


def _walk_and_normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _walk_and_normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_and_normalize(v) for v in obj]
    if isinstance(obj, str):
        return _normalize_string(obj)
    return obj


def _maybe_fix_percent_units(original_text: str, parsed: Dict[str, Any]) -> None:
    # Guard: only attempt for responsibilities lists
    if not isinstance(parsed, dict):
        return
    text = original_text or ""
    # Build a small index of percents present in original
    # e.g., find numbers followed by % and cache as strings
    import re
    percent_numbers = set(re.findall(r"(\d{1,3})%", text))

    exp_list = parsed.get("experience", []) if isinstance(parsed.get("experience"), list) else []
    for exp in exp_list:
        if not isinstance(exp, dict):
            continue
        responsibilities = exp.get("responsibilities", [])
        if not isinstance(responsibilities, list):
            continue
        fixed = []
        for line in responsibilities:
            if isinstance(line, str):
                m = re.search(r"\b(\d{1,3})(?=\b(?!%))\b(?!\s*%)", line)
                if m and m.group(1) in percent_numbers and "%" not in line:
                    # Append % to the number occurrence conservatively
                    num = m.group(1)
                    line = line.replace(num, num + "%", 1)
            fixed.append(line)
        exp["responsibilities"] = fixed


def normalize_resume_data(original_text: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Unicode and minor unit formatting without removing diacritics.
    Also conservatively add % symbol when the original text contains the same number followed by %.
    """
    # If it's already a dict, use it directly. Otherwise try to convert
    if isinstance(data, dict):
        as_dict = data
    else:
        try:
            as_dict = data.dict()
        except Exception:
            return data
    # Unicode/whitespace normalization across the structure
    normalized = _walk_and_normalize(as_dict)
    # Minor percent fix based on original text context
    _maybe_fix_percent_units(original_text, normalized.get("parsed_resume", normalized))
    return normalized