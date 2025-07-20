"""Semantic Router for intelligent plugin selection based on query meaning.

This module implements the semantic routing logic that uses LLM APIs to
understand user queries and route them to appropriate plugins.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from pydantic import BaseModel, Field
import structlog
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser

from src.core.plugin_system.plugin_interface import PluginMetadata, PluginRequest, PluginResponse
from src.core.plugin_system.plugin_manager import PluginManager
from src.core.protocol.mcp_protocol import MCPProtocol, MCPClient
from src.core.llm import LLMProviderFactory, LLMProvider, LLMMessage, MessageRole
from src.core.exceptions import RoutingDecisionError, MultiStepExecutionError, NoPluginsAvailableError
from src.config.settings import settings

logger = structlog.get_logger(__name__)


class RoutingDecision(BaseModel):
    """Represents a routing decision made by the semantic router."""
    
    plugin_name: str = Field(..., description="Name of the selected plugin")
    confidence: float = Field(..., description="Confidence score (0-1)")
    reasoning: str = Field(..., description="Explanation for the routing decision")
    extracted_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters extracted from the query"
    )


class MultiStepPlan(BaseModel):
    """Represents a multi-step execution plan."""
    
    steps: List[Dict[str, Any]] = Field(
        ...,
        description="List of steps to execute"
    )
    reasoning: str = Field(..., description="Overall plan reasoning")


class SemanticRouter:
    """Semantic router for intelligent plugin selection and orchestration."""
    
    def __init__(
        self,
        plugin_manager: PluginManager,
        llm_provider: Optional[LLMProvider] = None,
        temperature: float = 0.0
    ) -> None:
        """Initialize the semantic router.
        
        Args:
            plugin_manager: Plugin manager instance
            llm_provider: LLM provider instance (creates default if not provided)
            temperature: Temperature for LLM generation
        """
        self.plugin_manager = plugin_manager
        self.temperature = temperature
        
        # Use shared LLM provider for cost efficiency and consistent behavior
        if llm_provider:
            self.llm_provider = llm_provider
        else:
            # Create default provider when none specified to ensure functionality
            self.llm_provider = LLMProviderFactory.create_provider(
                provider_name=settings.llm_provider,
                api_key=settings.get_llm_api_key(),
                model=settings.get_llm_model()
            )
        
        # Output parsers
        self.routing_parser = PydanticOutputParser(pydantic_object=RoutingDecision)
        self.planning_parser = PydanticOutputParser(pydantic_object=MultiStepPlan)
        
        # Prompt templates
        self.routing_template = ChatPromptTemplate.from_messages([
            ("system", self._get_routing_system_prompt()),
            ("user", "{query}\n\nAvailable plugins:\n{plugins_info}")
        ])
        
        self.planning_template = ChatPromptTemplate.from_messages([
            ("system", self._get_planning_system_prompt()),
            ("user", "{query}\n\nAvailable plugins:\n{plugins_info}")
        ])
        
        self.mcp_protocol = MCPProtocol()
        self.mcp_client = MCPClient(self.mcp_protocol)
    
    def _get_routing_system_prompt(self) -> str:
        """Generate the system prompt for routing decisions.
        
        Creates a detailed prompt that instructs the LLM on how to:
        - Analyze user queries for intent
        - Match queries to available plugins
        - Extract relevant parameters
        - Provide confidence scores
        
        Returns:
            System prompt string for routing
        """
        return """You are a semantic router that analyzes user queries and routes them to appropriate plugins.
        
Your task is to:
1. Understand the user's intent from their query
2. Select the most appropriate plugin from available options
3. Extract relevant parameters from the query
4. Provide a confidence score (0-1) for your routing decision

You MUST respond with ONLY a JSON object (no additional text, no markdown formatting).

Example response format:
{{
    "plugin": "linkedin_external",
    "confidence": 0.95,
    "reasoning": "User is asking for LinkedIn profile information",
    "parameters": {{
        "username": "johndoe"
    }}
}}

Important:
- Response must be valid JSON only
- Use "plugin" not "plugin_name" 
- Use "parameters" not "extracted_params"
- Do not wrap in markdown code blocks
- Do not include any text before or after the JSON
"""
    
    def _get_planning_system_prompt(self) -> str:
        """Generate the system prompt for multi-step planning.
        
        Creates a prompt that guides the LLM to:
        - Break complex queries into steps
        - Identify dependencies between steps
        - Plan efficient execution order
        - Consider plugin capabilities
        
        Returns:
            System prompt string for planning
        """
        return """You are a task planner that creates multi-step execution plans for complex queries.
        
Your task is to:
1. Analyze if the query requires multiple steps
2. Break down complex tasks into individual plugin calls
3. Identify dependencies between steps
4. Create an efficient execution plan

Consider:
- Some steps may depend on outputs from previous steps
- Steps should be as atomic as possible
- Use available plugin capabilities effectively
- Provide clear reasoning for your plan"""
    
    def _format_plugins_info(self, plugins: Dict[str, PluginMetadata]) -> str:
        """Format plugin information for the LLM.
        
        Args:
            plugins: Plugin metadata dictionary
            
        Returns:
            str: Formatted plugin information
        """
        formatted_info = []
        
        for name, metadata in plugins.items():
            info = f"Plugin: {name}\n"
            info += f"  Description: {metadata.description}\n"
            info += f"  Capabilities: {', '.join(metadata.capabilities)}\n"
            
            if metadata.required_params:
                # Escape braces in the params to prevent template interpretation
                params_str = str(metadata.required_params).replace('{', '{{').replace('}', '}}')
                info += f"  Required params: {params_str}\n"
            
            if metadata.optional_params:
                # Escape braces in the params to prevent template interpretation
                params_str = str(metadata.optional_params).replace('{', '{{').replace('}', '}}')
                info += f"  Optional params: {params_str}\n"
                
            if metadata.examples:
                info += "  Examples:\n"
                # Limit examples to avoid token bloat
                # Most LLMs have context limits, so we balance informativeness with efficiency
                for example in metadata.examples[:2]:
                    info += f"    - {example.get('description', 'No description')}\n"
                    
            formatted_info.append(info)
            
        return "\n".join(formatted_info)
    
    async def route(self, query: str) -> RoutingDecision:
        """Route a query to the appropriate plugin.
        
        Args:
            query: The user query to route
            
        Returns:
            RoutingDecision: The routing decision
        """
        logger.info("Routing query", query=query)
        
        # Validate plugin availability to provide meaningful error early
        plugins = self.plugin_manager.get_all_plugin_metadata()
        
        if not plugins:
            raise NoPluginsAvailableError()
        
        # Format plugin information
        plugins_info = self._format_plugins_info(plugins)
        
        # Create the prompt
        prompt = self.routing_template.format_messages(
            query=query,
            plugins_info=plugins_info
        )
        
        try:
            # Convert prompt messages to LLM format
            messages = []
            for msg in prompt:
                role = MessageRole.SYSTEM if msg.type == "system" else MessageRole.USER
                messages.append(LLMMessage(role=role, content=msg.content))
            
            # Use LLM provider with JSON mode for structured output
            response = await self.llm_provider.complete(
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"}  # Enable JSON mode
            )
            
            logger.debug("LLM raw response", content=response.content)
            
            # Strip markdown formatting that LLMs sometimes add to JSON responses
            if response.content.startswith("```"):
                content = response.content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            # Parse JSON directly without using PydanticOutputParser
            import json
            try:
                # Clean the response
                content = response.content.strip()
                
                # Remove markdown code blocks if present
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end > start:
                        content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    if end > start:
                        content = content[start:end].strip()
                
                # Parse JSON
                data = json.loads(content)
                logger.info("Successfully parsed JSON", data=data)
                
                # Map common LLM response format to our expected schema
                routing_decision = RoutingDecision(
                    plugin_name=data.get("plugin", ""),
                    confidence=data.get("confidence", 0.0),
                    reasoning=data.get("reasoning", "Selected based on query analysis"),
                    extracted_params=data.get("parameters", {})
                )
                
                logger.info("Created routing decision", decision=routing_decision.dict())
                
            except json.JSONDecodeError as e:
                logger.error("JSON parsing failed", error=str(e), content=content)
                raise RoutingDecisionError(
                    f"Failed to parse JSON from LLM response: {str(e)}",
                    {"response": response.content, "error": str(e)}
                )
            except Exception as e:
                logger.error("Failed to create RoutingDecision", error=str(e), data=data)
                raise RoutingDecisionError(
                    f"Failed to create routing decision: {str(e)}",
                    {"response": response.content, "error": str(e)}
                )
            
            # Infer action for plugins that need it
            routing_decision = self._infer_plugin_action(query, routing_decision)
            
        except Exception as e:
            # Log error but don't expose internal details
            logger.error("Failed to route query", error=str(e))
            raise RoutingDecisionError(
                "Failed to determine appropriate plugin for query",
                {"query": query, "error": str(e)}
            )
        
        logger.info(
            "Routing decision made",
            plugin=routing_decision.plugin_name,
            confidence=routing_decision.confidence
        )
        return routing_decision
    
    def _infer_plugin_action(self, query: str, routing_decision: RoutingDecision) -> RoutingDecision:
        """Infer the specific action for plugins that need it.
        
        Some plugins like LinkedIn need specific actions (get_profile, scrape_company)
        rather than just the plugin name. This method infers the action from the query.
        
        Args:
            query: The original user query
            routing_decision: The routing decision to enhance
            
        Returns:
            Enhanced routing decision with action in extracted_params
        """
        # LinkedIn plugin requires action specification for proper tool selection
        if routing_decision.plugin_name == "linkedin_external":
            query_lower = query.lower()
            
            # Infer action based on query content
            if any(word in query_lower for word in ["company", "companies", "organization", "firm"]):
                action = "get_company"
                # Extract company name if not already in params
                if "company_name" not in routing_decision.extracted_params:
                    # Try to extract company name from query
                    # This is a simple heuristic - could be improved with NLP
                    import re
                    # Look for quoted company names or proper nouns
                    quoted = re.findall(r'"([^"]*)"', query)
                    if quoted:
                        routing_decision.extracted_params["company_name"] = quoted[0]
            else:
                # Default to profile scraping
                action = "get_profile"
                # Ensure we have either linkedin_username or username in params
                if "linkedin_username" not in routing_decision.extracted_params:
                    if "username" in routing_decision.extracted_params:
                        routing_decision.extracted_params["linkedin_username"] = routing_decision.extracted_params["username"]
                    elif "profile" in routing_decision.extracted_params:
                        routing_decision.extracted_params["linkedin_username"] = routing_decision.extracted_params["profile"]
            
            # Add the action to extracted params
            routing_decision.extracted_params["action"] = action
            
            logger.info(
                "Inferred action for LinkedIn plugin",
                action=action,
                params=routing_decision.extracted_params
            )
        
        return routing_decision
    
    async def plan_multi_step(self, query: str) -> MultiStepPlan:
        """Create a multi-step execution plan for complex queries.
        
        Args:
            query: The user query to plan for
            
        Returns:
            MultiStepPlan: The execution plan
        """
        logger.info("Planning multi-step execution", query=query)
        
        # Get available plugins
        plugins = self.plugin_manager.get_all_plugin_metadata()
        plugins_info = self._format_plugins_info(plugins)
        
        # Create planning prompt
        prompt = self.planning_template.format_messages(
            query=query,
            plugins_info=plugins_info
        )
        
        try:
            # Convert prompt messages to LLM format
            messages = []
            for msg in prompt:
                role = MessageRole.SYSTEM if msg.type == "system" else MessageRole.USER
                messages.append(LLMMessage(role=role, content=msg.content))
            
            # Use LLM provider with JSON mode for structured output
            response = await self.llm_provider.complete(
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"}  # Enable JSON mode
            )
            
            plan = self.planning_parser.parse(response.content)
        except Exception as e:
            logger.error("Failed to create multi-step plan", error=str(e))
            raise MultiStepExecutionError(
                "Failed to create execution plan",
                {"query": query, "error": str(e)}
            )
    
    async def execute_single(
        self,
        query: str,
        routing_decision: Optional[RoutingDecision] = None
    ) -> PluginResponse:
        """Execute a single plugin based on routing decision.
        
        Args:
            query: The original query
            routing_decision: Pre-computed routing decision (optional)
            
        Returns:
            PluginResponse: The plugin's response
        """
        # Get routing decision if not provided
        if routing_decision is None:
            routing_decision = await self.route(query)
        
        # Determine the action - use from extracted_params if available
        action = routing_decision.extracted_params.get("action", routing_decision.plugin_name)
        
        # Remove action from params to prevent double-passing to plugin
        if "action" in routing_decision.extracted_params:
            del routing_decision.extracted_params["action"]
        
        request = PluginRequest(
            request_id=f"req_{datetime.utcnow().timestamp()}",
            action=action,
            parameters=routing_decision.extracted_params
        )
        
        response = await self.plugin_manager.execute_plugin(
            routing_decision.plugin_name,
            request
        )
        
        return response
    
    async def execute_multi_step(
        self,
        query: str,
        plan: Optional[MultiStepPlan] = None
    ) -> List[PluginResponse]:
        """Execute a multi-step plan.
        
        Args:
            query: The original query
            plan: Pre-computed execution plan (optional)
            
        Returns:
            List[PluginResponse]: Responses from each step
        """
        # Get plan if not provided
        if plan is None:
            plan = await self.plan_multi_step(query)
        
        responses = []
        step_results = {}
        
        # Validate dependencies to prevent execution failures
        for i, step in enumerate(plan.steps):
            if "depends_on" in step:
                for dep_idx in step["depends_on"]:
                    if dep_idx >= i:
                        raise RoutingDecisionError(
                            f"Step {i}",
                            f"Invalid dependency: step {i} depends on unexecuted step {dep_idx}"
                        )
            
            # Prepare context with previous results
            context = {
                "previous_results": responses,
                "step_index": i,
                "total_steps": len(plan.steps)
            }
            
            plugin_name = step["plugin_name"]
            parameters = step.get("parameters", {})
            parameters["_context"] = context
            
            request = PluginRequest(
                request_id=f"req_{datetime.utcnow().timestamp()}_step_{i}",
                action=plugin_name,
                parameters=parameters
            )
            
            response = await self.plugin_manager.execute_plugin(
                plugin_name,
                request
            )
            
            responses.append(response)
        
        return responses
    
    async def analyze_complexity(self, query: str) -> Tuple[bool, str]:
        """Analyze if a query requires multi-step execution.
        
        Args:
            query: The query to analyze
            
        Returns:
            Tuple[bool, str]: (is_complex, reasoning)
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze if this query requires multiple steps or can be handled by a single plugin.
            
Consider it multi-step if it:
- Requires data from one plugin to feed into another
- Asks for multiple distinct operations
- Needs sequential processing
- Combines results from different sources

Respond with:
- is_complex: true/false
- reasoning: brief explanation"""),
            ("user", query)
        ])
        
        messages = prompt.format_messages(query=query)
        try:
            # Convert prompt messages to LLM format
            llm_messages = []
            for msg in messages:
                role = MessageRole.SYSTEM if msg.type == "system" else MessageRole.USER
                llm_messages.append(LLMMessage(role=role, content=msg.content))
            
            # Use LLM provider
            response = await self.llm_provider.complete(
                messages=llm_messages,
                temperature=0.0
            )
            
            content = response.content.lower()
            is_complex = "is_complex: true" in content or "true" in content.split("\n")[0]
            
            # Extract reasoning
            reasoning = response.content.strip()
            
        except Exception as e:
            # Default to simple on error
            logger.warning("Failed to analyze complexity", error=str(e))
            is_complex = False
            reasoning = "Defaulting to simple execution due to analysis error"
        
        return is_complex, reasoning
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a query end-to-end with automatic routing.
        
        Args:
            query: The user query
            
        Returns:
            Dict[str, Any]: Processing results
        """
        logger.info("Processing query", query=query)
        
        # Analyze complexity
        is_complex, reasoning = await self.analyze_complexity(query)
        
        if is_complex:
            # Multi-step execution
            plan = await self.plan_multi_step(query)
            responses = await self.execute_multi_step(query, plan)
            
            return {
                "type": "multi_step",
                "plan": plan.dict(),
                "responses": [r.dict() for r in responses],
                "reasoning": reasoning
            }
        else:
            # Single-step execution
            routing = await self.route(query)
            response = await self.execute_single(query, routing)
            
            return {
                "type": "single_step",
                "routing": routing.dict(),
                "response": response.dict(),
                "reasoning": reasoning
            } 