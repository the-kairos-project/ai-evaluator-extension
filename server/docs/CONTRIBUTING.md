# Contributing to MCP Server

Thank you for your interest in contributing to the MCP Server project! This document provides guidelines and best practices for contributing.

## Code Style

- **Python**: Follow PEP 8, use type hints, 88 character line length (Black)
- **Naming**: Classes: `PascalCase`, Functions: `snake_case`, Constants: `UPPER_CASE`
- **Tools**: Run `make format lint` before committing

## Comment Guidelines

Comments should explain **why** something is done, not **what** is being done.

### Good Comments
```python
# Use shared LLM provider for cost efficiency and consistent behavior
if llm_provider:
    self.llm_provider = llm_provider

# Validate dependencies to prevent execution failures
for i, step in enumerate(plan.steps):
    if "depends_on" in step:
        ...
```

### Poor Comments
```python
# Create LLM provider
llm_provider = LLMProviderFactory.create_provider()

# Loop through steps
for i, step in enumerate(plan.steps):
    ...
```

### Docstrings
All public classes, functions, and methods must have Google-style docstrings:

```python
def process_query(self, query: str, max_retries: int = 3) -> Dict[str, Any]:
    """Process a natural language query through the plugin system.
    
    Args:
        query: Natural language query to process
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary containing the processing results
        
    Raises:
        RoutingException: If no suitable plugin is found
    """
```

## Testing

- Write tests for all new functionality
- Maintain test coverage above 80%
- Place tests in appropriate directories: `tests/unit/` or `tests/integration/`

## Development Setup

```bash
# Install dependencies
pip install poetry
poetry install
pre-commit install

# Configure environment
cp example.env .env
# Edit .env with your settings
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the guidelines
4. Run tests and linting: `make test lint`
5. Commit with descriptive message: `git commit -m 'fix: improve error handling'`
6. Push to your fork: `git push origin feature/amazing-feature`
7. Open a Pull Request with a clear description

## PR Checklist

- [ ] Tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Code follows style guidelines
- [ ] Comments explain "why" not "what"
- [ ] Docstrings are complete
- [ ] No sensitive data in commits

## Contact

If you have questions or need help:
- Open an issue for discussion
- Join our community Discord server: [MCP Server Discord](https://discord.gg/mcp-server)
- Email the maintainers: mcp-maintainers@example.com 