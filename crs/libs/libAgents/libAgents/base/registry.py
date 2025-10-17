import logging
from typing import Any, Dict, List, Optional

from libAgents.base import ActionPlugin, PluginState
from libAgents.types import ResponseSchema

logger = logging.getLogger(__name__)


class ActionRegistry:
    """Registry for managing action plugins."""

    def __init__(self):
        self._plugins: Dict[str, ActionPlugin] = {}
        self._plugin_states: Dict[str, PluginState] = {}

    def register(self, plugin: ActionPlugin) -> None:
        """
        Register a new plugin.

        Args:
            plugin: The plugin to register

        Raises:
            ValueError: If a plugin with the same name is already registered
        """
        if plugin.action_name in self._plugins:
            raise ValueError(f"Plugin {plugin.action_name} is already registered")
        self._plugins[plugin.action_name] = plugin
        self._plugin_states[plugin.action_name] = PluginState(
            enabled=True, data={}, history=[]
        )

    def get_plugin(self, action_name: str) -> Optional[ActionPlugin]:
        """
        Get a plugin by its action name.

        Args:
            action_name: The name of the action

        Returns:
            The plugin if found, None otherwise
        """
        return self._plugins.get(action_name)

    def get_plugins(self) -> List[ActionPlugin]:
        """
        Get all registered plugins.

        Returns:
            List of all registered plugins
        """
        return list(self._plugins.values())

    def get_enabled_plugins(self) -> List[ActionPlugin]:
        """
        Get all enabled plugins.
        """
        return [
            plugin
            for plugin in self.get_plugins()
            if self.get_plugin_state(plugin.action_name).enabled
        ]

    def has_plugin(self, action_name: str) -> bool:
        """
        Check if a plugin is registered.
        """
        return action_name in self._plugins

    def get_plugin_state(self, action_name: str) -> PluginState:
        """
        Get the state of a plugin.
        """
        return self._plugin_states[action_name]

    def set_plugin_enabled(self, action_name: str, enabled: bool):
        """
        Set the enabled state of a plugin.
        """
        if action_name in self._plugin_states:
            self._plugin_states[action_name].enabled = enabled
        else:
            raise ValueError(f"Plugin {action_name} is not registered")

    def reset_all_plugin_states(self):
        """
        Reset the state of all plugins.
        """
        for action_name in self._plugin_states:
            self._plugin_states[action_name] = PluginState(
                enabled=True, data={}, history=[]
            )

    def disable_all_plugins(self):
        """
        Disable all plugins.
        """
        for action_name in self._plugin_states:
            self.set_plugin_enabled(action_name, False)

    def enable_all_plugins(self):
        """
        Enable all plugins.
        """
        for action_name in self._plugin_states:
            self.set_plugin_enabled(action_name, True)

    def disable_plugin(self, action_name: str):
        """
        Disable a plugin.
        """
        if action_name in self._plugin_states:
            self.set_plugin_enabled(action_name, False)

    def enable_plugin(self, action_name: str):
        """
        Enable a plugin.
        """
        if action_name in self._plugin_states:
            self.set_plugin_enabled(action_name, True)

    def get_schema_from_plugins(
        self, session, plugins: Optional[List[ActionPlugin]] = None
    ) -> ResponseSchema:
        """
        Generate a JSON schema with all possible action parameters merged into a single object.
        This approach avoids using 'anyOf' which is not supported by many language models.
        Defaults to using only enabled plugins if no specific list is provided.

        Args:
            plugins: List of plugins to include in the schema. If None, uses currently enabled plugins.

        Returns:
            ResponseSchema: The generated schema with a root type: object.
        """
        # Use provided plugins or default to currently enabled plugins
        plugins_to_use = plugins if plugins is not None else self.get_enabled_plugins()

        # Collect action names and merge all properties
        action_names: List[str] = []
        merged_properties: Dict[str, Any] = {}
        property_to_actions: Dict[str, List[str]] = {}  # Track which actions use which properties

        for plugin in plugins_to_use:
            action_names.append(plugin.action_name)
            plugin_properties = plugin.get_schema_properties(session)

            if plugin_properties:
                # Merge properties from this plugin
                for prop_name, prop_schema in plugin_properties.items():
                    if prop_name in merged_properties:
                        # Property exists in multiple plugins
                        property_to_actions[prop_name].append(plugin.action_name)
                        # Update description to indicate multiple actions use this property
                        existing_desc = merged_properties[prop_name].get("description", "")
                        merged_properties[prop_name]["description"] = (
                            f"{existing_desc} (Used by actions: {', '.join(property_to_actions[prop_name])})"
                        )
                    else:
                        # New property
                        merged_properties[prop_name] = prop_schema.copy()
                        property_to_actions[prop_name] = [plugin.action_name]
                        # Add action info to description
                        original_desc = prop_schema.get("description", "")
                        merged_properties[prop_name]["description"] = (
                            f"{original_desc} (Used by action: {plugin.action_name})"
                        )

        # Construct the final root schema
        final_schema: ResponseSchema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": action_names,
                    "description": "The specific action to perform.",
                },
                "thoughts": {
                    "type": "string",
                    "description": "Explain why choose this action, what's the thought process behind choosing this action",
                },
                "action-details": {
                    "type": "object",
                    "properties": merged_properties,
                    "description": "REQUIRED: Parameters for the chosen action. This object MUST be included even if empty. Only fill in parameters that are relevant to your selected action. Each parameter's description indicates which action(s) it belongs to.",
                    "additionalProperties": False,  # Prevent extra properties
                    "required": list(merged_properties.keys()),
                },
            },
            "required": ["action", "thoughts", "action-details"],
            "additionalProperties": False,  # Prevent extra properties at root level
        }

        # Handle case where no plugins are available/enabled
        if not plugins_to_use:
            # Return a minimal schema indicating no actions are possible
            return {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "No actions available.",
                        "enum": [],
                    },
                    "thoughts": {
                        "type": "string",
                        "description": "Reasoning (no actions possible).",
                    },
                    "action-details": {
                        "type": "object",
                        "properties": {},
                        "description": "No action parameters available.",
                    },
                },
                "required": ["action", "thoughts", "action-details"],
            }

        return final_schema
