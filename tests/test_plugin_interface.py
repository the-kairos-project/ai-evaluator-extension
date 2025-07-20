"""Tests for plugin interface."""

import pytest
from src.core.plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse


class TestPlugin(Plugin):
    """Test implementation of Plugin interface."""
    
    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test",
            capabilities=["test"],
            required_params={"message": "Test message"}
        )
    
    async def initialize(self, config=None):
        self._initialized = True
    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        return PluginResponse(
            request_id=request.request_id,
            status="success",
            data={"echo": request.parameters.get("message", "")}
        )
    
    async def shutdown(self):
        self._initialized = False
    
    def get_metadata(self) -> PluginMetadata:
        return self._metadata


@pytest.mark.asyncio
async def test_plugin_lifecycle():
    """Test plugin lifecycle methods."""
    plugin = TestPlugin()
    
    # Test metadata
    metadata = plugin.get_metadata()
    assert metadata.name == "test_plugin"
    assert metadata.version == "1.0.0"
    
    # Test initialization
    assert not plugin.is_initialized
    await plugin.initialize()
    assert plugin.is_initialized
    
    # Test execution
    request = PluginRequest(
        action="test",
        parameters={"message": "Hello"}
    )
    response = await plugin.execute(request)
    assert response.status == "success"
    assert response.data["echo"] == "Hello"
    
    # Test shutdown
    await plugin.shutdown()
    assert not plugin.is_initialized


@pytest.mark.asyncio
async def test_plugin_validation():
    """Test plugin request validation."""
    plugin = TestPlugin()
    
    # Valid request
    valid_request = PluginRequest(
        action="test",
        parameters={"message": "Test"}
    )
    assert await plugin.validate_request(valid_request)
    
    # Invalid request (missing required param)
    invalid_request = PluginRequest(
        action="test",
        parameters={}
    )
    assert not await plugin.validate_request(invalid_request) 