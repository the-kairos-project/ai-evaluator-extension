# MCP Server Plugins

This directory contains documentation for the various plugins available in the MCP Server.

## Available Plugins

- [PDF Resume Parser](pdf_resume_parser.md): Extract structured data from PDF resumes
- [LinkedIn External Plugin](linkedin_plugin.md): Scrape LinkedIn profiles and company pages

## Plugin Development

To create a new plugin, follow these steps:

1. Create a new Python file in `src/plugins/`:

```python
from src.core.plugin_system.plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="My awesome plugin",
            capabilities=["capability1", "capability2"]
        )
    
    async def initialize(self, config=None):
        self._initialized = True
    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        return PluginResponse(
            request_id=request.request_id,
            status="success",
            data={"result": "Hello from my plugin!"}
        )
    
    def get_metadata(self) -> PluginMetadata:
        return self._metadata
```

2. Add the plugin to `src/plugins/__init__.py`:

```python
from .my_plugin import MyPlugin

__all__ = [..., "MyPlugin"]
```

3. Create documentation for your plugin in `docs/plugins/my_plugin.md`

## Plugin Architecture

Plugins in the MCP Server follow a standard interface defined in `src/core/plugin_system/plugin_interface.py`. Each plugin must implement the following methods:

- `initialize`: Initialize the plugin with optional configuration
- `execute`: Execute the plugin's main functionality
- `shutdown`: Clean up resources when the plugin is unloaded
- `get_metadata`: Return metadata about the plugin

Plugins are loaded dynamically by the PluginManager and can be hot-reloaded during development.