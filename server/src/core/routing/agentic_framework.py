"""Agentic Framework for intelligent task orchestration with reflection.

This module implements the cognitive framework that enables planning,
execution, and self-correcting reflection loops.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import json
from src.utils.logging import get_structured_logger
from langchain.prompts import ChatPromptTemplate

from src.core.routing.semantic_router import SemanticRouter, MultiStepPlan, RoutingDecision
from src.core.plugin_system.plugin_interface import PluginResponse
from src.core.llm import LLMProviderFactory, LLMProvider, LLMMessage, MessageRole
from src.config.settings import settings

logger = get_structured_logger(__name__)


class TaskGoal(BaseModel):
    """Represents the goal of a task."""
    
    description: str = Field(..., description="Goal description")
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Criteria for successful completion"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Constraints or limitations"
    )


class ExecutionResult(BaseModel):
    """Result of task execution."""
    
    status: str = Field(..., description="success, partial, or failed")
    data: Any = Field(None, description="Result data")
    steps_completed: int = Field(0, description="Number of steps completed")
    total_steps: int = Field(0, description="Total number of steps")
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReflectionAnalysis(BaseModel):
    """Analysis from reflection phase."""
    
    goal_achieved: bool = Field(..., description="Whether the goal was achieved")
    missing_aspects: List[str] = Field(
        default_factory=list,
        description="What's missing from the result"
    )
    quality_assessment: str = Field(..., description="Assessment of result quality")
    suggested_improvements: List[str] = Field(
        default_factory=list,
        description="Suggested improvements or next steps"
    )
    needs_retry: bool = Field(False, description="Whether to retry with improvements")
    retry_strategy: Optional[str] = Field(None, description="Strategy for retry if needed")


class AgenticFramework:
    """Framework for planning, executing, and reflecting on complex tasks."""
    
    def __init__(
        self,
        semantic_router: SemanticRouter,
        llm_provider: Optional[LLMProvider] = None,
        max_retries: int = 3,
        temperature: float = 0.0
    ) -> None:
        """Initialize the agentic framework.
        
        Args:
            semantic_router: Semantic router instance
            llm_provider: LLM provider instance (creates default if not provided)
            max_retries: Maximum retry attempts
            temperature: Temperature for LLM generation
        """
        self.semantic_router = semantic_router
        self.max_retries = max_retries
        self.temperature = temperature
        
        # Create LLM provider if not provided
        if llm_provider:
            self.llm_provider = llm_provider
        else:
            # Use settings to create default provider
            self.llm_provider = LLMProviderFactory.create_provider(
                provider_name=settings.llm_provider,
                api_key=settings.get_llm_api_key(),
                model=settings.get_llm_model()
            )
        
        # Prompt templates
        self.goal_extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_goal_extraction_prompt()),
            ("user", "{query}")
        ])
        
        self.reflection_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_reflection_prompt()),
            ("user", "Goal: {goal}\nSuccess Criteria: {success_criteria}\nResult: {result}")
        ])
        
        self.improvement_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI that improves queries based on reflection feedback."),
            ("user", "Original query: {query}\nStrategy: {strategy}\nImprovements: {improvements}\n\nGenerate an improved query.")
        ])
    
    def _get_goal_extraction_prompt(self) -> str:
        """Get the system prompt for goal extraction."""
        return """Extract the goal and success criteria from the user query.
        
Identify:
1. The main goal/objective
2. Specific success criteria (what would make this successful)
3. Any constraints or limitations mentioned

Format as JSON with:
- description: main goal
- success_criteria: list of criteria
- constraints: list of constraints"""
    
    def _get_reflection_prompt(self) -> str:
        """Get the system prompt for reflection."""
        return """Analyze the execution result against the original goal.

Consider:
1. Was the goal achieved?
2. What aspects are missing or incomplete?
3. How good is the quality of the result?
4. What improvements could be made?
5. Should we retry with a different approach?

Format as JSON with:
- goal_achieved: boolean
- missing_aspects: list of what's missing
- quality_assessment: brief assessment
- suggested_improvements: list of improvements
- needs_retry: boolean
- retry_strategy: strategy if retry needed"""
    
    async def extract_goal(self, query: str) -> TaskGoal:
        """Extract the goal from a user query.
        
        Args:
            query: The user query
            
        Returns:
            TaskGoal: The extracted goal
        """
        logger.info("Extracting goal from query", query=query)
        
        prompt = self.goal_extraction_prompt.format_messages(query=query)
        try:
            # Convert prompt messages to LLM format
            messages = []
            for msg in prompt:
                role = MessageRole.SYSTEM if msg.type == "system" else MessageRole.USER
                messages.append(LLMMessage(role=role, content=msg.content))
            
            response = await self.llm_provider.complete(
                messages=messages,
                temperature=self.temperature
            )
            response_content = response.content
        except Exception as e:
            logger.error("Failed to extract goal", error=str(e))
            # Fallback to simple goal
            return TaskGoal(
                description=query,
                success_criteria=["Complete the requested task"],
                constraints=[]
            )
        
        # Parse response (simplified - could use structured output)
        try:
            import json
            data = json.loads(response_content)
            return TaskGoal(
                description=data.get("description", query),
                success_criteria=data.get("success_criteria", []),
                constraints=data.get("constraints", [])
            )
        except Exception as e:
            logger.warning("Failed to parse goal extraction", error=str(e))
            return TaskGoal(description=query)
    
    async def plan(self, query: str, goal: TaskGoal) -> Dict[str, Any]:
        """Create an execution plan based on the goal.
        
        Args:
            query: The user's query
            goal: The extracted goal
            
        Returns:
            Execution plan dictionary
        """
        logger.info("Creating execution plan", goal=goal.description)
        
        # Analyze complexity
        is_complex = await self.semantic_router.analyze_complexity(query)
        
        if is_complex[0]:
            # Get multi-step plan
            plan = await self.semantic_router.plan_multi_step(query)
            return {
                "type": "multi_step",
                "plan": plan.dict(),
                "complexity_reasoning": is_complex[1]
            }
        else:
            # Get routing decision
            routing = await self.semantic_router.route(query)
            return {
                "type": "single_step",
                "routing": routing.dict(),
                "complexity_reasoning": is_complex[1]
            }
    
    async def execute(
        self,
        query: str,
        plan: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute the plan and return results.
        
        Args:
            query: The user's query
            plan: The execution plan
            
        Returns:
            Execution result with status and data
        """
        logger.info("Executing plan", plan_type=plan.get("type"))
        
        try:
            if plan["type"] == "multi_step":
                # Execute multi-step plan
                responses = await self.semantic_router.execute_multi_step(
                    query,
                    MultiStepPlan(**plan["plan"])
                )
                
                # Aggregate results
                all_data = []
                for response in responses:
                    if response.success:
                        all_data.append(response.data)
                
                return ExecutionResult(
                    status="success" if all(r.success for r in responses) else "partial",
                    data=all_data,
                    steps_completed=len(responses),
                    total_steps=len(plan["plan"]["steps"]),
                    errors=[r.error for r in responses if r.error]
                )
            else:
                # Execute single step
                response = await self.semantic_router.execute_single(
                    query,
                    RoutingDecision(**plan["routing"])
                )
                
                return ExecutionResult(
                    status="success" if response.success else "failed",
                    data=response.data,
                    steps_completed=1,
                    total_steps=1,
                    errors=[response.error] if response.error else []
                )
        
        except Exception as e:
            logger.error("Execution failed", error=str(e))
            return ExecutionResult(
                status="failed",
                errors=[str(e)]
            )
    
    async def reflect(
        self,
        goal: TaskGoal,
        result: ExecutionResult
    ) -> ReflectionAnalysis:
        """Analyze the execution result against the goal.
        
        Args:
            goal: The original goal
            result: The execution result
            
        Returns:
            Reflection analysis with assessment and suggestions
        """
        logger.info("Reflecting on execution", status=result.status)
        
        # Format result for analysis
        result_summary = {
            "status": result.status,
            "data": result.data,
            "errors": result.errors,
            "completion": f"{result.steps_completed}/{result.total_steps}"
        }
        
        prompt = self.reflection_prompt.format_messages(
            goal=goal.description,
            success_criteria="\n".join(goal.success_criteria),
            result=json.dumps(result_summary, indent=2)
        )
        
        try:
            # Convert prompt messages to LLM format
            messages = []
            for msg in prompt:
                role = MessageRole.SYSTEM if msg.type == "system" else MessageRole.USER
                messages.append(LLMMessage(role=role, content=msg.content))
            
            response = await self.llm_provider.complete(
                messages=messages,
                temperature=self.temperature
            )
            response_content = response.content
        except Exception as e:
            logger.error("Failed to reflect on result", error=str(e))
            # Default reflection
            return ReflectionAnalysis(
                goal_achieved=result.status == "success",
                missing_aspects=[],
                quality_assessment="Unable to analyze",
                suggested_improvements=[],
                needs_retry=False
            )
        
        # Parse response
        try:
            data = json.loads(response_content)
            return ReflectionAnalysis(
                goal_achieved=data.get("goal_achieved", False),
                missing_aspects=data.get("missing_aspects", []),
                quality_assessment=data.get("quality_assessment", ""),
                suggested_improvements=data.get("suggested_improvements", []),
                needs_retry=data.get("needs_retry", False),
                retry_strategy=data.get("retry_strategy")
            )
        except Exception as e:
            logger.warning("Failed to parse reflection", error=str(e))
            return ReflectionAnalysis(
                goal_achieved=result.status == "success",
                quality_assessment="Unable to parse detailed reflection"
            )
    
    async def process_with_reflection(
        self,
        query: str,
        max_attempts: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a query with full reflection loop.
        
        Args:
            query: The user query
            max_attempts: Maximum attempts (overrides default)
            
        Returns:
            Dict[str, Any]: Complete processing result
        """
        max_attempts = max_attempts or self.max_retries
        
        # Extract goal
        goal = await self.extract_goal(query)
        
        attempts = 0
        current_query = query
        all_results = []
        
        while attempts < max_attempts:
            attempts += 1
            # Log attempt number
            logger.info("Processing attempt", attempt=attempts, max_attempts=max_attempts)
            
            # Plan
            plan = await self.plan(current_query, goal)
            
            # Execute
            result = await self.execute(current_query, plan)
            
            # Reflect
            reflection = await self.reflect(goal, result)
            
            all_results.append({
                "attempt": attempts,
                "plan": plan,
                "result": result.dict(),
                "reflection": reflection.dict()
            })
            
            # Check if goal achieved or no retry needed
            if reflection.goal_achieved or not reflection.needs_retry:
                break
            
            # Prepare for retry with improvements
            if attempts < max_attempts:
                # Modify query based on reflection
                current_query = await self._improve_query(
                    query,
                    reflection.retry_strategy or "",
                    reflection.suggested_improvements
                )
                logger.info("Retrying with improved query", new_query=current_query)
        
        # Final result
        final_result = all_results[-1]["result"]
        final_reflection = all_results[-1]["reflection"]
        
        return final_result
    
    async def _improve_query(
        self,
        original_query: str,
        retry_strategy: str,
        improvements: List[str]
    ) -> str:
        """Improve the query based on reflection feedback.
        
        Args:
            original_query: The original query
            retry_strategy: The suggested retry strategy
            improvements: Suggested improvements
            
        Returns:
            str: Improved query
        """
        prompt = self.improvement_prompt.format_messages(
            query=original_query,
            strategy=retry_strategy,
            improvements=", ".join(improvements)
        )
        
        try:
            # Convert prompt messages to LLM format
            messages = []
            for msg in prompt:
                role = MessageRole.SYSTEM if msg.type == "system" else MessageRole.USER
                messages.append(LLMMessage(role=role, content=msg.content))
            
            response = await self.llm_provider.complete(
                messages=messages,
                temperature=self.temperature
            )
            return response.content
        except Exception as e:
            logger.error("Failed to improve query", error=str(e))
            # Return original query on error
            return original_query
    
    async def explain_reasoning(
        self,
        processing_result: Dict[str, Any]
    ) -> str:
        """Generate a human-readable explanation of the processing.
        
        Args:
            processing_result: The complete processing result
            
        Returns:
            str: Human-readable explanation
        """
        prompt = f"""Explain the reasoning behind this processing result:

Query: {processing_result.get('original_query', 'Unknown')}
Goal: {processing_result.get('goal', {}).get('description', 'Unknown')}
Attempts: {processing_result.get('total_attempts', 0)}
Final Status: {processing_result.get('final_status', 'Unknown')}

Provide a clear explanation of what was done and why."""
        
        try:
            messages = [
                LLMMessage(role=MessageRole.SYSTEM, content="You are an AI that explains processing results."),
                LLMMessage(role=MessageRole.USER, content=prompt)
            ]
            
            response = await self.llm_provider.complete(
                messages=messages,
                temperature=self.temperature
            )
            return response.content
        except Exception as e:
            logger.error("Failed to explain reasoning", error=str(e))
            return "Unable to generate explanation due to an error." 