#!/usr/bin/env python3
"""
Plugin Manager for Thor Robotic Arm

Handles discovery, loading, and lifecycle management of plugins.
"""

import os
import sys
import importlib
import importlib.util
from typing import List, Dict, Optional
from pathlib import Path
from plugin_base import Plugin, PluginMetadata


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.

    The PluginManager scans the plugins directory for Python files,
    loads them, and manages their lifecycle (initialize, enable, disable, shutdown).
    """

    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, Plugin] = {}
        self.plugin_modules: Dict[str, any] = {}

    def discover_plugins(self) -> List[str]:
        """
        Discover all available plugins in the plugins directory.

        Returns:
            List of plugin file paths
        """
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created plugins directory: {self.plugins_dir}")
            return []

        # Find all Python files in plugins directory (excluding __init__.py and private files)
        plugin_files = []
        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            plugin_files.append(str(file_path))

        return plugin_files

    def load_plugin(self, plugin_path: str) -> Optional[Plugin]:
        """
        Load a single plugin from a file.

        Args:
            plugin_path: Path to the plugin Python file

        Returns:
            Loaded Plugin instance, or None if loading failed
        """
        try:
            # Get module name from file path
            module_name = Path(plugin_path).stem

            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                print(f"Failed to load spec for {plugin_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find Plugin subclass in the module
            plugin_class = None
            for item_name in dir(module):
                item = getattr(module, item_name)
                # Check if it's a class, subclass of Plugin, and not Plugin itself
                if (isinstance(item, type) and
                    issubclass(item, Plugin) and
                    item is not Plugin):
                    plugin_class = item
                    break

            if plugin_class is None:
                print(f"No Plugin subclass found in {plugin_path}")
                return None

            # Instantiate the plugin
            plugin_instance = plugin_class()

            # Store the module for potential reloading
            self.plugin_modules[module_name] = module

            print(f"✓ Loaded plugin: {plugin_instance.get_metadata().name}")
            return plugin_instance

        except Exception as e:
            print(f"✗ Failed to load plugin {plugin_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_all_plugins(self, gui_app) -> Dict[str, Plugin]:
        """
        Discover and load all plugins from the plugins directory.

        Args:
            gui_app: The main GUI application instance

        Returns:
            Dictionary mapping plugin names to Plugin instances
        """
        plugin_files = self.discover_plugins()
        print(f"\nDiscovered {len(plugin_files)} plugin(s)")

        for plugin_file in plugin_files:
            plugin = self.load_plugin(plugin_file)
            if plugin:
                # Initialize the plugin
                try:
                    success = plugin.initialize(gui_app)
                    if success:
                        plugin_name = plugin.get_metadata().name
                        self.loaded_plugins[plugin_name] = plugin
                        print(f"  ✓ Initialized: {plugin_name}")
                    else:
                        print(f"  ✗ Failed to initialize plugin from {plugin_file}")
                except Exception as e:
                    print(f"  ✗ Error initializing plugin: {e}")
                    import traceback
                    traceback.print_exc()

        print(f"Successfully loaded {len(self.loaded_plugins)} plugin(s)\n")
        return self.loaded_plugins

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a loaded plugin by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        return self.loaded_plugins.get(plugin_name)

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            True if successful, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = True
            print(f"Enabled plugin: {plugin_name}")
            return True
        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            True if successful, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = False
            print(f"Disabled plugin: {plugin_name}")
            return True
        return False

    def reload_plugin(self, plugin_name: str, gui_app) -> bool:
        """
        Reload a plugin (shutdown, unload, reload, initialize).

        Args:
            plugin_name: Name of the plugin to reload
            gui_app: The main GUI application instance

        Returns:
            True if successful, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return False

        try:
            # Shutdown the plugin
            plugin.shutdown()

            # Find the original plugin file
            module_name = None
            for name, mod in self.plugin_modules.items():
                if hasattr(mod, plugin.__class__.__name__):
                    module_name = name
                    break

            if not module_name:
                print(f"Could not find module for {plugin_name}")
                return False

            # Remove from loaded plugins
            del self.loaded_plugins[plugin_name]

            # Reload the module
            plugin_path = self.plugins_dir / f"{module_name}.py"
            new_plugin = self.load_plugin(str(plugin_path))

            if new_plugin:
                success = new_plugin.initialize(gui_app)
                if success:
                    self.loaded_plugins[plugin_name] = new_plugin
                    print(f"✓ Reloaded plugin: {plugin_name}")
                    return True

        except Exception as e:
            print(f"✗ Failed to reload plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()

        return False

    def shutdown_all(self):
        """Shutdown all loaded plugins"""
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                plugin.shutdown()
                print(f"Shutdown plugin: {plugin_name}")
            except Exception as e:
                print(f"Error shutting down {plugin_name}: {e}")

    def get_all_plugins(self) -> Dict[str, Plugin]:
        """Get all loaded plugins"""
        return self.loaded_plugins

    def get_plugins_with_ui(self) -> Dict[str, Plugin]:
        """Get all plugins that have a UI widget"""
        return {
            name: plugin
            for name, plugin in self.loaded_plugins.items()
            if plugin.create_widget() is not None
        }

    def trigger_robot_connected(self):
        """Notify all plugins that robot connected"""
        for plugin in self.loaded_plugins.values():
            if plugin.enabled:
                try:
                    plugin.on_robot_connected()
                except Exception as e:
                    print(f"Error in {plugin.get_metadata().name}.on_robot_connected: {e}")

    def trigger_robot_disconnected(self):
        """Notify all plugins that robot disconnected"""
        for plugin in self.loaded_plugins.values():
            if plugin.enabled:
                try:
                    plugin.on_robot_disconnected()
                except Exception as e:
                    print(f"Error in {plugin.get_metadata().name}.on_robot_disconnected: {e}")

    def trigger_joint_moved(self, joint_id: str, angle: float):
        """Notify all plugins that a joint moved"""
        for plugin in self.loaded_plugins.values():
            if plugin.enabled:
                try:
                    plugin.on_joint_moved(joint_id, angle)
                except Exception as e:
                    print(f"Error in {plugin.get_metadata().name}.on_joint_moved: {e}")

    def trigger_kinect_frame(self, rgb_frame, depth_frame):
        """Notify all plugins of new Kinect frame"""
        for plugin in self.loaded_plugins.values():
            if plugin.enabled:
                try:
                    plugin.on_kinect_frame(rgb_frame, depth_frame)
                except Exception as e:
                    print(f"Error in {plugin.get_metadata().name}.on_kinect_frame: {e}")

    def trigger_sensor_update(self, joint_id: str, sensor_data: Dict):
        """Notify all plugins of sensor update"""
        for plugin in self.loaded_plugins.values():
            if plugin.enabled:
                try:
                    plugin.on_sensor_update(joint_id, sensor_data)
                except Exception as e:
                    print(f"Error in {plugin.get_metadata().name}.on_sensor_update: {e}")
