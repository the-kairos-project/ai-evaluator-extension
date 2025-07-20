"""Plugin system components."""

from .plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse
from .plugin_manager import PluginManager

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginRequest",
    "PluginResponse",
    "PluginManager",
]
