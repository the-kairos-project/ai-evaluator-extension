"""Calculator plugin for evaluating mathematical expressions."""

import ast
import operator
import math
from typing import Dict, Any, Optional, Union
from src.utils.logging import get_structured_logger

from src.core.plugin_system.plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse
from src.core.exceptions import ExpressionValidationError, PluginExecutionError

logger = get_structured_logger(__name__)

# Safe operators for evaluation - prevents arbitrary code execution
# We use AST parsing instead of eval() to ensure only mathematical
# operations are performed, preventing security vulnerabilities
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class MathEvaluator:
    """Safe mathematical expression evaluator."""
    
    def __init__(self) -> None:
        self.allowed_names = {
            'pi': math.pi,
            'e': math.e,
        }
        
        self.allowed_functions = {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'sqrt': math.sqrt,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'abs': abs,
            'round': round,
        }
    
    def _validate_node(self, node: ast.AST) -> None:
        """Validate AST node for safety."""
        if isinstance(node, ast.Constant):
            # Only allow specific constants like pi and e
            if node.value in self.allowed_names.values():
                return
            # Regular numeric constants are always safe
            if isinstance(node.value, (int, float, complex)):
                return
            raise ExpressionValidationError(
                f"Unsafe constant: {node.value}",
                {"node_type": type(node).__name__, "value": node.value}
            )
        
        elif isinstance(node, ast.Name):
            if node.id not in self.allowed_names:
                raise ExpressionValidationError(
                    f"Unsafe name: {node.id}",
                    {"name": node.id}
                )
        
        elif isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and 
                   node.func.id in self.allowed_functions):
                raise ExpressionValidationError(
                    f"Unsafe function call: {getattr(node.func, 'id', 'unknown')}",
                    {"function": getattr(node.func, 'id', 'unknown')}
                )
        
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in SAFE_OPERATORS:
                raise ExpressionValidationError(
                    f"Unsafe operation: {type(node.op).__name__}",
                    {"operation": type(node.op).__name__}
                )
            self._validate_node(node.left)
            self._validate_node(node.right)
        
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in SAFE_OPERATORS:
                raise ExpressionValidationError(
                    f"Unsafe operation: {type(node.op).__name__}",
                    {"operation": type(node.op).__name__}
                )
            self._validate_node(node.operand)
        
        else:
            raise ExpressionValidationError(
                f"Unsupported node type: {type(node).__name__}",
                {"node_type": type(node).__name__}
            )
    
    def _evaluate_node(self, node: ast.AST) -> Union[int, float, complex]:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Name):
            if node.id in self.allowed_names:
                return self.allowed_names[node.id]
            raise ExpressionValidationError(
                f"Unknown variable: {node.id}",
                {"variable": node.id}
            )
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate_node(node.operand)
            return SAFE_OPERATORS[type(node.op)](operand)
        
        elif isinstance(node, ast.BinOp):
            left = self._evaluate_node(node.left)
            right = self._evaluate_node(node.right)
            return SAFE_OPERATORS[type(node.op)](left, right)
        
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.allowed_functions:
                func = self.allowed_functions[node.func.id]
                args = [self._evaluate_node(arg) for arg in node.args]
                return func(*args)
            raise ExpressionValidationError(
                f"Function not allowed: {getattr(node.func, 'id', 'unknown')}",
                {"function": getattr(node.func, 'id', 'unknown')}
            )
        
        else:
            raise ExpressionValidationError(
                f"Unsupported expression type: {type(node).__name__}",
                {"node_type": type(node).__name__}
            )
    
    def evaluate(self, expression: str) -> Union[int, float, complex]:
        """Safely evaluate a mathematical expression."""
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise ExpressionValidationError(
                f"Invalid expression syntax: {e}",
                {"expression": expression, "error": str(e)}
            )
        
        self._validate_node(tree.body)
        
        try:
            result = self._evaluate_node(tree.body)
            return result
        except Exception as e:
            raise ExpressionValidationError(
                f"Evaluation error: {e}",
                {"expression": expression, "error": str(e)}
            )


class CalculatorPlugin(Plugin):
    """A plugin that performs mathematical calculations."""
    
    def __init__(self) -> None:
        """Initialize the math evaluator with allowed operations."""
        super().__init__()
        self.evaluator = MathEvaluator()
        self._metadata = PluginMetadata(
            name="calculator",
            version="1.0.0",
            description="Performs mathematical calculations and evaluations",
            author="MCP Team",
            capabilities=["calculate", "math", "arithmetic", "evaluate"],
            required_params={
                "expression": "Mathematical expression to evaluate"
            },
            optional_params={
                "precision": "Number of decimal places for the result",
                "format": "Output format: 'number', 'scientific', or 'fraction'"
            },
            examples=[
                {
                    "query": "Calculate 2 + 2",
                    "parameters": {"expression": "2 + 2"}
                },
                {
                    "query": "What is 15% of 200?",
                    "parameters": {"expression": "200 * 0.15"}
                },
                {
                    "query": "Calculate the area of a circle with radius 5",
                    "parameters": {"expression": "3.14159 * 5**2"}
                }
            ]
        )
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin.
        
        Args:
            config: Optional configuration
        """
        logger.info("Initializing Calculator plugin", config=config)
        self._initialized = True
    

    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        """Execute the calculation.
        
        Args:
            request: The plugin request
            
        Returns:
            PluginResponse: The calculation result
        """
        try:
            expression = request.parameters.get("expression")
            if not expression:
                raise PluginExecutionError(
                    self.metadata.name,
                    "No expression provided",
                    {"parameters": request.parameters}
                )
            
            logger.info("Evaluating expression", expression=expression)
            
            result = self.evaluator.evaluate(expression)
            
            # Format the result nicely
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            
            return PluginResponse(
                plugin_name=self.metadata.name,
                success=True,
                data={
                    "expression": expression,
                    "result": result,
                    "type": type(result).__name__
                },
                metadata={
                    "execution_time": "0ms"
                }
            )
            
        except Exception as e:
            logger.error("Calculator plugin execution failed", error=str(e))
            return PluginResponse(
                request_id=request.request_id,
                status="error",
                error=str(e)
            )
    
    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info("Shutting down Calculator plugin")
        self._initialized = False
    
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata.
        
        Returns:
            PluginMetadata: The plugin's metadata
        """
        return self._metadata 