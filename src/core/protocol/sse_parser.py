"""
Server-Sent Events (SSE) Parser Utility.

This module provides utilities for parsing SSE responses from MCP servers.
"""

import json
from typing import Any, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class SSEParseError(Exception):
    """Exception raised when SSE parsing fails."""
    pass


class SSEParser:
    """Parser for Server-Sent Events format."""
    
    @staticmethod
    def parse_event(text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse an SSE event from text.
        
        Args:
            text: Raw SSE text containing event and data
            
        Returns:
            Tuple of (event_type, parsed_data)
            
        Raises:
            SSEParseError: If parsing fails
        """
        if not text:
            raise SSEParseError("Empty SSE text")
            
        event_type = None
        data = None
        
        # Split into lines, handling both \n and \r\n
        lines = text.replace('\r\n', '\n').split('\n')
        
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_line = line[6:].strip()
                if data_line:
                    try:
                        data = json.loads(data_line)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "Failed to parse SSE data as JSON",
                            data=data_line,
                            error=str(e)
                        )
                        # Return raw data if not JSON
                        data = {"raw": data_line}
        
        return event_type, data
    
    @staticmethod
    def extract_mcp_response(text: str) -> Dict[str, Any]:
        """Extract MCP response from SSE text.
        
        Args:
            text: Raw SSE text from MCP server
            
        Returns:
            Parsed MCP response data
            
        Raises:
            SSEParseError: If no valid MCP response found
        """
        event_type, data = SSEParser.parse_event(text)
        
        if not data:
            raise SSEParseError("No data found in SSE response")
            
        # Validate it's a message event
        if event_type and event_type != "message":
            logger.warning(
                "Unexpected SSE event type",
                event_type=event_type,
                expected="message"
            )
        
        return data
    
    @staticmethod
    def parse_mcp_result(text: str) -> Tuple[bool, Any, Optional[str]]:
        """Parse MCP result from SSE response.
        
        Args:
            text: Raw SSE text from MCP server
            
        Returns:
            Tuple of (success, result_or_error, error_message)
        """
        try:
            data = SSEParser.extract_mcp_response(text)
            
            if "result" in data:
                return True, data["result"], None
            elif "error" in data:
                error = data["error"]
                error_msg = error.get("message", "Unknown error") if isinstance(error, dict) else str(error)
                return False, error, error_msg
            else:
                logger.warning("MCP response missing result or error", data=data)
                return False, None, "Invalid MCP response format"
                
        except SSEParseError as e:
            return False, None, str(e)
        except Exception as e:
            logger.error("Unexpected error parsing MCP response", error=str(e))
            return False, None, f"Parse error: {str(e)}" 