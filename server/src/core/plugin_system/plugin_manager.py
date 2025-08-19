"""Plugin Manager for dynamic plugin discovery and lifecycle management.

This module handles the discovery, loading, initialization, and management
of plugins in the MCP Server.
"""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from src.utils.logging import get_structured_logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse
from ..exceptions import (
    PluginNotFoundError,
    PluginInitializationError,
    PluginExecutionError,
    PluginValidationError,
    PluginLoadError,
)


logger = get_structured_logger(__name__)


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
            
        # Import plugins from the __init__.py file (standard Python behavior)
        try:
            logger.info("Importing plugins from __init__.py")
            import src.plugins as plugins_module
            
            # Look for plugin classes in the module
            for name in dir(plugins_module):
                obj = getattr(plugins_module, name)
                
                # Check if it's a plugin class
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj is not Plugin):
                    
                    # Try to get metadata
                    try:
                        # Instantiate to get metadata
                        temp_instance = obj()
                        metadata = temp_instance.get_metadata()
                        plugin_name = metadata.name
                        
                        # Register plugin
                        self.available_plugins[plugin_name] = obj
                        logger.debug(
                            "Discovered plugin from __init__",
                            name=plugin_name,
                            class_name=obj.__name__
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to get plugin metadata from __init__",
                            class_name=name,
                            error=str(e)
                        )
        except Exception as e:
            logger.error("Failed to import plugins from __init__", error=str(e))
            
        # Next, scan for plugin files in main directory
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
                
        # Also check subdirectories for plugin.py files
        for file_path in self.plugin_directory.glob("*/plugin.py"):
            if file_path.parent.name.startswith("_"):
                continue
                
            try:
                # For subdirectory plugins, use the directory name as the module name
                dir_name = file_path.parent.name
                module_path = f"src.plugins.{dir_name}.plugin"
                logger.info(f"Loading plugin from subdirectory: {file_path} as {module_path}")
                
                # Use the directory name for the module override
                self._load_plugin_module(file_path, module_name_override=module_path)
            except Exception as e:
                logger.error(
                    "Failed to load plugin module from subdirectory",
                    file=str(file_path),
                    error=str(e),
                    exc_info=True
                )
                
        # Log discovered plugins summary
        if self.available_plugins:
            logger.info(
                f"Plugin discovery completed: {len(self.available_plugins)} plugins available"
            )
            logger.debug(
                "Available plugins",
                plugins=list(self.available_plugins.keys())
            )
        else:
            logger.warning("No plugins discovered")
    
    def _load_plugin_module(self, file_path: Path, module_name_override: str = None) -> None:
        """Load a plugin module and register its Plugin classes.
        
        Args:
            file_path: Path to the plugin Python file
            module_name_override: Optional override for module name (used for subdirectories)
        """
        module_name = module_name_override if module_name_override else file_path.stem
        logger.debug(f"Loading plugin module: {module_name} from {file_path}")
        
        # First try if the module is already importable (e.g., from __init__.py)
        if "." in module_name:
            try:
                logger.debug(f"Trying to import {module_name} directly")
                module = importlib.import_module(module_name)
                logger.debug(f"Successfully imported {module_name} directly")
            except ImportError as e:
                # If direct import fails, try spec-based loading
                logger.debug(f"Direct import failed, trying spec-based loading: {str(e)}")
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                else:
                    logger.error(f"Failed to get spec for {module_name} from {file_path}")
                    return
        else:
            # For simple module names, use spec-based loading
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            else:
                logger.error(f"Failed to get spec for {module_name} from {file_path}")
                return
            
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
                        logger.debug(
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
    
    async def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> Plugin:
        """Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            config: Optional configuration for the plugin
            
        Returns:
            The loaded plugin instance
            
        Raises:
            PluginNotFoundError: If plugin not found
            PluginLoadError: If plugin loading fails
        """
        # Check if the plugin is already loaded
        if plugin_name in self.loaded_plugins:
            logger.debug(f"Plugin '{plugin_name}' already loaded, returning cached instance")
            return self.loaded_plugins[plugin_name]
        
        # Check if plugin is in available plugins
        if plugin_name in self.available_plugins:
            logger.debug(f"Loading plugin from available plugins: {plugin_name}")
            # Get the plugin class directly from available_plugins
            plugin_class = self.available_plugins[plugin_name]
        else:
            # Detailed logging of what's available
            logger.error(f"Plugin '{plugin_name}' not found in available plugins")
            logger.debug(f"Available plugins: {list(self.available_plugins.keys())}")
            raise PluginNotFoundError(plugin_name)
        
        logger.debug(f"Loading plugin: {plugin_name}")
        
        try:
            # Use the plugin class we already have
            logger.debug(f"Found plugin class: {plugin_class.__name__}")
            
            # Create an instance of the plugin
            plugin = plugin_class()
            logger.debug(f"Created plugin instance: {plugin_class.__name__}")
            
            # Initialize the plugin
            try:
                await plugin.initialize(config)
                logger.debug(f"Plugin '{plugin_name}' initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize plugin '{plugin_name}': {str(e)}", exc_info=True)
                raise PluginInitializationError(plugin_name, str(e))
            
            # Store the plugin instance
            self.loaded_plugins[plugin_name] = plugin
            logger.info(f"Plugin {plugin_name} ready")
            
            return plugin
            
        except Exception as e:
            if not isinstance(e, (PluginNotFoundError, PluginLoadError, PluginInitializationError)):
                logger.error(f"Unexpected error loading plugin '{plugin_name}': {str(e)}", exc_info=True)
                raise PluginLoadError(plugin_name, str(e))
            raise
    
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