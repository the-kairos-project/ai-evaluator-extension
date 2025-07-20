"""Plugin Manager for dynamic plugin discovery and lifecycle management.

This module handles the discovery, loading, initialization, and management
of plugins in the MCP Server.
"""

import importlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import structlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse
from ..exceptions import (
    PluginNotFoundError,
    PluginInitializationError,
    PluginExecutionError,
    PluginValidationError,
)


logger = structlog.get_logger(__name__)


class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot-reloading."""
    
    def __init__(self, plugin_manager: "PluginManager") -> None:
        """Initialize the file handler.
        
        Args:
            plugin_manager: Reference to the plugin manager for callbacks.
        """
        self.plugin_manager = plugin_manager
        
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.
        
        Args:
            event: File system event containing path and event type.
        """
        if not event.is_directory and event.src_path.endswith('.py'):
            logger.info("Plugin file modified", path=event.src_path)
            self.plugin_manager._reload_plugin_from_path(Path(event.src_path))
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.
        
        Args:
            event: File system event containing path and event type.
        """
        if not event.is_directory and event.src_path.endswith('.py'):
            logger.info("New plugin file created", path=event.src_path)
            self.plugin_manager._load_plugin_module(Path(event.src_path))


class PluginManager:
    """Manages the lifecycle of plugins in the MCP Server."""
    
    def __init__(
        self,
        plugin_directory: str = "src/plugins",
        auto_reload: bool = False
    ) -> None:
        """Initialize the Plugin Manager.
        
        Args:
            plugin_directory: Directory containing plugin modules
            auto_reload: Whether to enable hot-reloading of plugins
        """
        self.plugin_directory = Path(plugin_directory)
        self.auto_reload = auto_reload
        self.available_plugins: Dict[str, Type[Plugin]] = {}
        self.loaded_plugins: Dict[str, Plugin] = {}
        self.observer: Optional[Observer] = None
        
        # Ensure plugin directory exists
        self.plugin_directory.mkdir(parents=True, exist_ok=True)
        
        # Enable imports from plugin directory by adding to Python path
        if str(self.plugin_directory) not in sys.path:
            sys.path.insert(0, str(self.plugin_directory))
    
    async def initialize(self) -> None:
        """Initialize the plugin manager and discover available plugins.
        
        This method should be called once during application startup to:
        1. Discover all available plugins in the plugin directory
        2. Set up file watching for hot-reload (if enabled)
        3. Prepare the plugin system for use
        """
        logger.info("Initializing plugin manager")
        await self.discover_plugins()
        
        if self.auto_reload:
            self._setup_file_watcher()
            
        logger.info(
            "Plugin manager initialized",
            available_plugins=len(self.available_plugins)
        )
    
    async def discover_plugins(self) -> None:
        """Discover and load all plugins from the plugin directory.
        
        This method scans the plugin directory for Python files containing
        plugin classes that inherit from PluginInterface. Each valid plugin
        is loaded and registered.
        
        Raises:
            PluginInitializationError: If a plugin fails to initialize
        """
        logger.info("Discovering plugins", directory=str(self.plugin_directory))
        
        self.available_plugins.clear()
        
        # Ensure directory is a valid Python package for proper imports
        init_file = self.plugin_directory / "__init__.py"
        if not init_file.exists():
            init_file.touch()
        
        # Scan for plugin files
        for file_path in self.plugin_directory.glob("*_plugin.py"):
            if file_path.name.startswith("_"):
                continue
                
            try:
                self._load_plugin_module(file_path)
            except Exception as e:
                logger.error(
                    "Failed to load plugin module",
                    file=str(file_path),
                    error=str(e)
                )
    
    def _load_plugin_module(self, file_path: Path) -> None:
        """Load a plugin module and register its Plugin classes.
        
        Args:
            file_path: Path to the plugin Python file
        """
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find Plugin subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj is not Plugin):
                    
                    try:
                        # Instantiate temporarily to read metadata without full initialization
                        # This avoids side effects while discovering available plugins
                        temp_instance = obj()
                        metadata = temp_instance.get_metadata()
                        plugin_name = metadata.name
                        
                        self.available_plugins[plugin_name] = obj
                        logger.info(
                            "Discovered plugin",
                            name=plugin_name,
                            class_name=obj.__name__,
                            file=str(file_path)
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to get plugin metadata",
                            class_name=obj.__name__,
                            error=str(e)
                        )
    
    async def load_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Plugin:
        """Load and initialize a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to load
            config: Optional configuration for the plugin
            
        Returns:
            The loaded and initialized plugin instance
            
        Raises:
            PluginNotFoundError: If plugin class not found
            PluginInitializationError: If plugin initialization fails
        """
        # Avoid duplicate loading which could cause state conflicts
        if plugin_name in self.loaded_plugins:
            return
        
        # Lazy loading: instantiate only when first accessed for efficiency
        if plugin_name not in self.available_plugins:
            raise PluginNotFoundError(plugin_name)
            
        plugin_class = self.available_plugins[plugin_name]
            
        try:
            plugin = plugin_class()
            
            await plugin.initialize(config)
            
            self.loaded_plugins[plugin_name] = plugin
            
            logger.info(
                "Plugin loaded successfully",
                plugin=plugin_name,
                metadata=plugin.get_metadata().dict()
            )
            
            return plugin
            
        except Exception as e:
            logger.error(
                "Failed to load plugin",
                plugin=plugin_name,
                error=str(e)
            )
            raise PluginInitializationError(plugin_name, str(e), e)
    
    async def unload_plugin(self, plugin_name: str) -> None:
        """Unload a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
        """
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            try:
                await plugin.shutdown()
                del self.loaded_plugins[plugin_name]
                logger.info("Plugin unloaded", name=plugin_name)
            except Exception as e:
                logger.error(
                    "Error shutting down plugin",
                    name=plugin_name,
                    error=str(e)
                )
    
    async def reload_plugins(self) -> None:
        """Reload all plugins by unloading and re-discovering them.
        
        This method provides a way to refresh the plugin system:
        1. Unloads all currently loaded plugins
        2. Re-discovers available plugins
        3. Useful for development or when plugins are updated
        
        Note: Existing plugin state will be lost during reload.
        """
        logger.info("Reloading all plugins")
        await self.shutdown_all_plugins()
        self.available_plugins.clear()
        await self.discover_plugins()
    
    async def execute_plugin(
        self,
        plugin_name: str,
        request: PluginRequest
    ) -> PluginResponse:
        """Execute a plugin with the given request.
        
        Args:
            plugin_name: Name of the plugin to execute
            request: The plugin request
            
        Returns:
            The plugin response
            
        Raises:
            PluginNotFoundError: If plugin not loaded
            PluginValidationError: If request validation fails
            PluginExecutionError: If plugin execution fails
        """
        if plugin_name not in self.loaded_plugins:
            # Try to load the plugin if it exists but isn't loaded
            if plugin_name in self.available_plugins:
                await self.load_plugin(plugin_name)
            else:
                raise PluginNotFoundError(plugin_name)
            
        plugin = self.loaded_plugins[plugin_name]
            
        try:
            # Validate request
            if not await plugin.validate_request(request):
                raise PluginValidationError(
                    plugin_name,
                    {"reason": "Request validation failed", "request": request.dict()}
                )
                    
            response = await plugin.execute(request)
                
            return response
            
        except PluginValidationError:
            raise
        except Exception as e:
            logger.error(
                "Plugin execution failed",
                plugin=plugin_name,
                action=request.action,
                error=str(e)
            )
            raise PluginExecutionError(
                plugin_name,
                request.action,
                str(e),
                e
            )
    
    def get_available_plugins(self) -> List[str]:
        """Get list of available plugin names.
        
        Returns:
            List[str]: Names of available plugins
        """
        return list(self.available_plugins.keys())
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names.
        
        Returns:
            List[str]: Names of loaded plugins
        """
        return list(self.loaded_plugins.keys())
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Optional[PluginMetadata]: Plugin metadata if found
        """
        # Check if already loaded
        if plugin_name in self.loaded_plugins:
            plugin_instance = self.loaded_plugins[plugin_name]
            try:
                return plugin_instance.get_metadata()
            except Exception as e:
                logger.error(
                    "Failed to get plugin metadata from loaded plugin",
                    plugin=plugin_name,
                    error=str(e)
                )
        
        # Check if available but not loaded
        elif plugin_name in self.available_plugins:
            plugin_class = self.available_plugins[plugin_name]
            try:
                # Read metadata without full initialization to avoid side effects
                temp_instance = plugin_class()
                return temp_instance.get_metadata()
            except Exception as e:
                logger.error(
                    "Failed to get plugin metadata from available plugin",
                    plugin=plugin_name,
                    error=str(e)
                )
        
        return None
    
    def get_all_plugin_metadata(self) -> Dict[str, PluginMetadata]:
        """Get metadata for all available plugins.
        
        Returns:
            Dict[str, PluginMetadata]: Mapping of plugin names to metadata
        """
        metadata = {}
        for plugin_name in self.available_plugins:
            plugin_metadata = self.get_plugin_metadata(plugin_name)
            if plugin_metadata:
                metadata[plugin_name] = plugin_metadata
        return metadata
    
    async def shutdown_all_plugins(self) -> None:
        """Shutdown all loaded plugins gracefully.
        
        This method ensures all plugins are properly cleaned up by:
        1. Calling shutdown() on each loaded plugin
        2. Removing them from the loaded plugins registry
        3. Logging any errors that occur during shutdown
        
        Should be called during application shutdown.
        """
        logger.info("Shutting down all plugins")
        for plugin_name in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_name)
            
    def _setup_file_watcher(self) -> None:
        """Set up file system watcher for plugin hot-reloading.
        
        Creates and starts a file system observer that monitors
        the plugin directory for changes. When files are modified
        or created, the appropriate handlers are called.
        
        Only active when auto_reload is True.
        """
        self.observer = Observer()
        self.observer.schedule(
            PluginFileHandler(self),
            self.plugin_directory,
            recursive=True
        )
        self.observer.start()
        logger.info("File watcher started for plugin hot-reload")
        
    async def shutdown(self) -> None:
        """Shutdown the plugin manager and cleanup resources.
        
        This method should be called during application shutdown to:
        1. Stop all loaded plugins
        2. Stop the file watcher (if running)
        3. Clean up any resources
        
        Safe to call multiple times.
        """
        await self.shutdown_all_plugins()
        
        if hasattr(self, 'observer') and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")
            
        logger.info("Plugin manager shutdown complete") 