"""
LinkedIn External Plugin for MCP Server

This plugin integrates with the external LinkedIn MCP server by stickerdaniel,
running it as a separate process and communicating via HTTP.
Only exposes profile and company scraping capabilities as requested.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import time

from src.utils.logging import get_structured_logger

from src.core.plugin_system.plugin_interface import Plugin, PluginRequest, PluginResponse, PluginMetadata
from src.core.external_mcp.external_mcp_client import ExternalMCPClient
from src.core.external_mcp.external_mcp_process import ExternalMCPProcess
from src.core.protocol.mcp_constants import (
    DEFAULT_LINKEDIN_TIMEOUT,
    LINKEDIN_MAX_RETRIES,
    LINKEDIN_MCP_PORT,
    LINKEDIN_STARTUP_TIMEOUT,
    DEFAULT_MCP_HOST,
)
from src.core.exceptions import (
    PluginInitializationError,
    ExternalProcessError,
    ConfigurationError,
    ValidationError,
)

logger = get_structured_logger(__name__)


class LinkedInExternalPlugin(Plugin):
    """LinkedIn plugin that integrates with external LinkedIn MCP server.
    
    This plugin provides LinkedIn profile and company scraping capabilities
    by managing an external LinkedIn MCP server process and communicating
    with it via HTTP/SSE protocol.
    """
    
    def __init__(self) -> None:
        """Initialize the LinkedIn external plugin.
        
        Sets up initial state and prepares for external server management.
        The actual server process is started during initialize().
        """
        super().__init__()
        self.process_manager: Optional[ExternalMCPProcess] = None
        self.mcp_client: Optional[ExternalMCPClient] = None
        self.server_url: Optional[str] = None
        self.linkedin_cookie: Optional[str] = None
        self.available_tools: List[str] = []
        logger.info("LinkedIn external plugin instance created")
        
        # Available tools from the external server (filtered)
        self.allowed_tools = {
            "get_person_profile": {
                "description": "Scrape a LinkedIn profile by username",
                "parameters": {
                    "linkedin_username": "LinkedIn username (e.g., 'john-doe-123456')"
                }
            },
            "get_company_profile": {
                "description": "Scrape a LinkedIn company profile by company name", 
                "parameters": {
                    "company_name": "LinkedIn company name (e.g., 'microsoft')",
                    "get_employees": "Whether to scrape employees (optional, default: false)"
                }
            }
        }
        
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the LinkedIn plugin and start external MCP server.
        
        This method:
        1. Loads LinkedIn cookie from settings
        2. Starts the external LinkedIn MCP server process
        3. Initializes MCP client connection
        4. Verifies available tools
        
        Args:
            config: Optional configuration dictionary (not currently used)
            
        Raises:
            PluginInitializationError: If server startup or connection fails
            ConfigurationError: If LinkedIn server not found
        """
        logger.info("Initializing LinkedIn external plugin")
        
        # LinkedIn cookie can come from config, environment, or request
        if config and "linkedin_cookie" in config:
            self.linkedin_cookie = config["linkedin_cookie"]
            logger.info("Using LinkedIn cookie from config")
        else:
            self.linkedin_cookie = os.getenv("LINKEDIN_COOKIE")
            if self.linkedin_cookie:
                logger.info("Using LinkedIn cookie from environment variable")
        
        if not self.linkedin_cookie:
            raise ConfigurationError(
                "linkedin_cookie",
                "LinkedIn cookie is required. Set LINKEDIN_COOKIE environment variable."
            )
        
        # Configure the external MCP server based on environment
        await self._setup_external_server(config)
        
        # Create the MCP client after server URL is set
        if self.server_url:
            self.mcp_client = ExternalMCPClient(
                self.server_url,
                timeout=DEFAULT_LINKEDIN_TIMEOUT,
                max_retries=LINKEDIN_MAX_RETRIES
            )
            logger.info("Created MCP client", url=self.server_url, timeout=DEFAULT_LINKEDIN_TIMEOUT)
            
            # Enter the context manager to create HTTP session
            await self.mcp_client.__aenter__()
            logger.info("MCP client HTTP session created")
        else:
            raise PluginInitializationError("Server URL not set after setup")
        
        # Initialize early if we have a cookie to avoid lazy initialization delays
        if self.linkedin_cookie and self.mcp_client:
            try:
                # Pre-establish the session to validate the cookie and reduce first-request latency
                await self.mcp_client.initialize_session()
                logger.info("LinkedIn MCP client initialized with session")
            except Exception as e:
                logger.warning("Failed to initialize MCP session", error=str(e))
                logger.info("LinkedIn MCP client prepared - will retry on first request")
        else:
            logger.info("LinkedIn MCP client prepared - no cookie provided yet")
        
        # Verify expected tools are available
        if self.mcp_client and hasattr(self.mcp_client, 'session_id') and self.mcp_client.session_id:
            tools = await self.mcp_client.list_tools()
            expected_tools = ["get_person_profile", "get_company_profile"]
            for tool_name in expected_tools:
                if not any(tool.get("name") == tool_name for tool in tools):
                    logger.warning("Expected tool not available in external server", tool=tool_name)
        
        logger.info("LinkedIn External plugin initialized successfully")
        self._initialized = True
        
    async def _setup_external_server(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Set up the external LinkedIn MCP server.
        
        This method determines whether to use an existing external server (Docker)
        or start a local instance based on the environment.
        """
        # Docker environments use a shared MCP server instance for resource efficiency
        is_docker = os.environ.get("DOCKER_ENV") == "true"
        
        if is_docker:
            # Running in Docker - connect to existing service
            self.server_url = os.getenv("LINKEDIN_EXTERNAL_SERVER_URL")
            if not self.server_url:
                raise ConfigurationError(
                    "LINKEDIN_EXTERNAL_SERVER_URL",
                    "LINKEDIN_EXTERNAL_SERVER_URL environment variable not set in Docker."
                )
            logger.info("Using external LinkedIn MCP server in Docker network", url=self.server_url)
            
            # In Docker mode, we don't start our own process
            self.process_manager = None
            
        else:
            # Running locally - start our own process
            host = DEFAULT_MCP_HOST
            port = LINKEDIN_MCP_PORT
            
            if config:
                host = config.get("external_server_host", host)
                port = config.get("external_server_port", port)
            
            self.server_url = f"http://{host}:{port}"
            
            # Find LinkedIn server
            linkedin_server_path = self._find_linkedin_server()
            if not linkedin_server_path:
                raise ConfigurationError(
                    "linkedin_server_path",
                    "LinkedIn MCP server not found. Please ensure external/linkedin-mcp-server directory exists."
                )
            
            # Create process manager for local execution
            self.process_manager = ExternalMCPProcess(
                server_path=linkedin_server_path,
                server_args=[],
                host=host,
                port=port,
                startup_timeout=LINKEDIN_STARTUP_TIMEOUT
            )
            
            # Start immediately with cookie to avoid authentication prompts in non-interactive mode
            server_args = [
                "run", 
                "--transport", "streamable-http",
                "--host", host,
                "--port", str(port),
                "--cookie", self.linkedin_cookie,
                "--no-lazy-init",  # Validate cookie upfront to fail fast if invalid
            ]
            
            # Apply the configuration to the process manager
            self.process_manager.server_args = server_args
            
            # Start the server
            try:
                await self.process_manager.start()
                logger.info("LinkedIn MCP server started successfully")
            except Exception as e:
                logger.error("Failed to start LinkedIn MCP server", error=str(e))
                command_str = f"python {linkedin_server_path} " + " ".join(server_args)
                raise ExternalProcessError(
                    command_str,
                    "Failed to start external LinkedIn MCP server",
                    None
                )
    
    def _find_linkedin_server(self) -> Optional[Path]:
        """Find the LinkedIn MCP server in the external directory.
        
        Searches for the server in common locations:
        1. external/linkedin-mcp-server/main.py
        2. external/linkedin-mcp-server/linkedin_mcp_server/main.py
        
        Returns:
            Path to the server script if found, None otherwise
        """
        # Look for the LinkedIn MCP server in expected locations
        possible_paths = [
            Path("external/linkedin-mcp-server/main.py"),
            Path("external/linkedin-mcp-server/linkedin_mcp_server/main.py"),
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info("Found LinkedIn MCP server", path=str(path))
                return path.resolve()
        
        logger.error("LinkedIn MCP server not found in expected locations")
        return None
    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        """Execute a LinkedIn scraping request.
        
        Handles two types of requests:
        1. Profile scraping - requires linkedin_username or profile URL
        2. Company scraping - requires company_name
        
        Args:
            request: Plugin request containing action and parameters
            
        Returns:
            PluginResponse with scraped data or error message
            
        The request.action can be:
        - "scrape_profile", "get_profile", "profile" for profiles
        - "scrape_company", "get_company", "company" for companies
        """
        if not self.mcp_client:
            logger.error("Plugin not initialized - MCP client is None")
            return PluginResponse(
                request_id=request.request_id,
                status="error",
                success=False,
                error="Plugin not initialized. Please check configuration."
            )
        
        logger.info("LinkedIn plugin received request", 
                   action=request.action,
                   parameters=request.parameters)
        
        logger.debug("====================== LINKEDIN EXTERNAL PLUGIN EXECUTION ======================")
        logger.debug(f"Request ID: {request.request_id}")
        logger.debug(f"Action: {request.action}")
        logger.debug(f"Parameters: {request.parameters}")
        logger.debug(f"Plugin state: initialized={self._initialized}, has_client={self.mcp_client is not None}")
        
        # Debug: Print detailed information about the plugin state
        logger.debug(f"LinkedIn plugin state: initialized={self._initialized}, has_client={self.mcp_client is not None}")
        if self.mcp_client:
            logger.debug(f"MCP client: url={self.server_url}, session_active={hasattr(self.mcp_client, 'session') and self.mcp_client.session is not None}")
            logger.debug(f"MCP client timeout: {self.mcp_client.timeout}s")
        
        try:
            # Check if server is healthy
            logger.debug("Performing health check on LinkedIn MCP server")
            logger.debug("Performing health check on LinkedIn MCP server...")
            health_check_result = await self.mcp_client.health_check()
            logger.debug(f"LinkedIn MCP server health check result: {health_check_result}")
            logger.debug(f"LinkedIn MCP server health check result: {health_check_result}")
            
            if not health_check_result:
                logger.warning("LinkedIn MCP server health check failed, attempting restart")
                if self.process_manager:
                    await self.process_manager.restart()
                await self.mcp_client.initialize_session()
                logger.info("LinkedIn MCP server restarted and session initialized")
            
            # Determine the tool to call and arguments based on request
            tool_name = ""
            tool_args = {}
            
            # Get the action from the request
            action = request.action.lower()
            logger.debug(f"Processing action: {action}")
            
            # Special handling for get_person_profile action
            if action == "get_person_profile":
                tool_name = "get_person_profile"
                linkedin_username = request.parameters.get("linkedin_username")
                if not linkedin_username:
                    logger.error("Missing required parameter: linkedin_username")
                    return PluginResponse(
                        request_id=request.request_id,
                        status="error",
                        error="Missing required parameter: linkedin_username"
                    )
                tool_args = {"linkedin_username": linkedin_username}
                logger.info(f"Using get_person_profile with username: {linkedin_username}")
            elif action in ["scrape_profile", "get_profile", "profile"]:
                profile_input = request.parameters.get("profile") or request.parameters.get("url") or request.parameters.get("username")
                logger.debug(f"Profile input: {profile_input}")
                
                if not profile_input:
                    logger.error("Profile URL or username is required")
                    raise ValidationError(
                        "profile",
                        None,
                        "Profile URL or username is required"
                    )

                # Extract parameters
                linkedin_username = request.parameters.get("linkedin_username", "")
                if not linkedin_username:
                    linkedin_username = self._extract_username_from_url(profile_input)
                    logger.debug(f"Extracted username from URL: {linkedin_username}")
                
                if not linkedin_username:
                    logger.error("linkedin_username parameter is required for profile scraping")
                    raise ValidationError(
                        "linkedin_username",
                        None,
                        "linkedin_username parameter is required for profile scraping"
                    )
                
                tool_name = "get_person_profile"
                tool_args = {"linkedin_username": linkedin_username}
                
            # Handle company scraping
            elif action in ["scrape_company", "get_company", "company"]:
                company_name = request.parameters.get("company_name", "")
                get_employees = request.parameters.get("get_employees", False)
                logger.debug(f"Company name: {company_name}, get_employees: {get_employees}")
                
                if not company_name:
                    logger.error("company_name parameter is required for company scraping")
                    raise ValidationError(
                        "company_name",
                        None,
                        "company_name parameter is required for company scraping"
                    )
                
                tool_name = "get_company_profile"
                tool_args = {"company_name": company_name}
                if get_employees:
                    tool_args["get_employees"] = True
                
            else:
                logger.error(f"Unknown action: {action}")
                raise ValidationError(
                    "action",
                    None,
                    "Could not determine scraping type. Provide 'action', 'url', 'linkedin_username', or 'company_name'"
                )
            
            # Verify tool is allowed
            if tool_name not in self.allowed_tools:
                logger.error(f"Tool '{tool_name}' is not allowed")
                return PluginResponse(
                    request_id=request.request_id,
                    status="error",
                    error=f"Tool '{tool_name}' is not allowed. Available tools: {list(self.allowed_tools.keys())}"
                )
            
            logger.info("Calling external LinkedIn MCP tool", tool=tool_name, args=tool_args)
            logger.debug(f"Starting tool call at {time.time()}")
            
            # Delegate to external server for actual LinkedIn API interaction
            response = await self.mcp_client.call_tool(tool_name, tool_args)
            logger.debug(f"Completed tool call at {time.time()}")
            logger.debug(f"Response is error: {response.isError}")
            
            if response.isError:
                error_text = ""
                for content in response.content:
                    if content.get("type") == "text":
                        error_text += content.get("text", "")
                
                logger.error(f"External MCP error: {error_text}")
                return PluginResponse(
                    request_id=request.request_id,
                    status="error",
                    error=f"External MCP error: {error_text}"
                )
            
            # Extract data from response
            data = None
            for content in response.content:
                if content.get("type") == "text":
                    data = content.get("text", "")
            
            logger.debug(f"Raw data type: {type(data)}")
            logger.debug(f"Raw data preview: {str(data)[:100]}..." if data else "None")
            
            # Try to parse as JSON if it looks like structured data
            # The LinkedIn MCP server sometimes returns JSON strings that need parsing
            if isinstance(data, str) and data.strip().startswith('{'):
                try:
                    data = json.loads(data)
                    logger.debug("Successfully parsed JSON data")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON data: {e}")
                    pass

            logger.info(f"LinkedIn plugin returning successful response with data length: {len(str(data)) if data else 0}")
            return PluginResponse(
                request_id=request.request_id,
                status="success",
                data=data,
                metadata={
                    "external_tool": tool_name,
                    "external_server": self.server_url,
                    "action_performed": tool_name
                }
            )
            
        except ValidationError as e:
            logger.error("Validation error during LinkedIn scraping", error=str(e))
            return PluginResponse(
                request_id=request.request_id,
                status="error",
                error=f"Validation error: {e.message}"
            )
        except Exception as e:
            logger.error("Error calling external MCP server", error=str(e), error_type=type(e).__name__)
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            return PluginResponse(
                request_id=request.request_id,
                status="error",
                error=f"Failed to call external LinkedIn MCP server: {error_msg}"
            )
    
    def _extract_username_from_url(self, url: str) -> str:
        """Extract LinkedIn username from profile URL.
        
        Args:
            url: LinkedIn profile URL (e.g., https://linkedin.com/in/username)
            
        Returns:
            Extracted username or empty string if not found
            
        Examples:
            - https://linkedin.com/in/johndoe -> johndoe
            - https://www.linkedin.com/in/jane-doe/ -> jane-doe
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'in':
                return path_parts[1]
        except Exception:
            pass
        return ""
    
    def _extract_company_from_url(self, url: str) -> str:
        """Extract company identifier from LinkedIn company URL.
        
        Args:
            url: LinkedIn company URL (e.g., https://linkedin.com/company/acme-corp)
            
        Returns:
            Extracted company identifier or empty string if not found
            
        Examples:
            - https://linkedin.com/company/microsoft -> microsoft
            - https://www.linkedin.com/company/google/ -> google
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'company':
                return path_parts[1]
        except Exception:
            pass
        return ""
    
    async def shutdown(self) -> None:
        """Shutdown the plugin and cleanup resources.
        
        This method ensures clean shutdown by:
        1. Closing the MCP client connection
        2. Stopping the external server process
        3. Cleaning up any resources
        
        Safe to call multiple times.
        """
        logger.info("Shutting down LinkedIn external plugin")
        
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
            self.mcp_client = None
            
        if self.process_manager:
            await self.process_manager.stop()
            self.process_manager = None
            
        logger.info("LinkedIn external plugin shutdown complete")
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata.
        
        Returns:
            PluginMetadata containing plugin information and capabilities
        """
        return PluginMetadata(
            name="linkedin_external",
            version="1.0.0",
            description="LinkedIn profile and company scraper via external MCP server",
            author="MCP Server Team",
            capabilities=[
                "scrape_profile",
                "get_profile", 
                "profile",
                "scrape_company",
                "get_company",
                "company"
            ],
            required_params={
                # Required params depend on the action
                # For profile: linkedin_username or profile URL
                # For company: company_name
            },
            optional_params={
                "get_employees": "For company scraping - whether to fetch employee list (boolean)"
            },
            tags=["linkedin", "scraping", "profiles", "companies", "external"]
        ) 