import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

# avoid circular import
if TYPE_CHECKING:
    from libAgents.session import ResearchSession


logger = logging.getLogger(__name__)

ENABLE_IN_NEXT_ROUND = True
DISABLE_IN_NEXT_ROUND = False


class ActionPluginError(Exception):
    """Base exception for action plugin errors."""

    pass


class PluginExecutionError(ActionPluginError):
    """Raised when there is an error executing a plugin."""

    pass


def handler_hook(func: Callable) -> Callable:
    """
    Decorator that handles context updates for plugin actions.
    Automatically updates session context after the handle method completes.
    """

    @wraps(func)
    async def wrapper(
        self: "ActionPlugin",
        session: "ResearchSession",
        current_question: str,
        *args,
        **kwargs,
    ) -> bool:
        try:
            # Call the original handle method
            result = await func(self, session, current_question, *args, **kwargs)

            # Prepare context update with complete information
            context_update = {
                "totalStep": session.total_step,
                "original_question": session.question,
                "current_question": current_question,
                "gaps": session.gaps,
                **session.this_step,
            }

            # Handle optional result data
            if isinstance(result, tuple) and len(result) == 2:
                continue_flag, result_data = result
                context_update["result"] = result_data
                result = continue_flag

            # print(f"context_update: {context_update}") # DEBUG PRINT

            # Update context with complete information
            session.update_context(context_update)

            # deal with plugin enable/disable
            session.enable_all_plugins()
            session.set_plugin_enabled(self.action_name, result)
            return result

        except Exception as e:
            logger.error(f"[{self.action_name}] Error: {e}")
            # Update context with error information
            session.update_context(
                {
                    "totalStep": session.total_step,
                    "original_question": session.question,
                    "current_question": current_question,
                    "gaps": session.gaps,
                    **session.this_step,
                    "error": str(e),
                }
            )
            # In the case of error, we want to disable the plugin and enable all other plugins
            # TODO: what if the plugin is answer plugin?
            session.enable_all_plugins()
            session.disable_plugin(self.action_name)
            return DISABLE_IN_NEXT_ROUND

    return wrapper


@dataclass
class PluginState:
    """State specific to a plugin."""

    enabled: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    last_error: Optional[Exception] = None

    def update(self, data: Dict[str, Any]) -> None:
        """Update the plugin's data."""
        self.data.update(data)

    def record_error(self, error: Exception) -> None:
        """Record an error in the plugin's state."""
        self.error_count += 1
        self.last_error = error

    def is_healthy(self) -> bool:
        """Check if the plugin is in a healthy state."""
        return self.error_count < 3  # Allow up to 3 errors before considering unhealthy

    def reset(self) -> None:
        """Reset the plugin's state."""
        self.error_count = 0
        self.last_error = None
        self.data.clear()

    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the plugin's recent history."""
        return self.history[-limit:]


class ActionPlugin(ABC):
    """
    Base class for all action plugins.
    Defines the interface that all plugins must implement.
    """

    @property
    @abstractmethod
    def action_name(self) -> str:
        """
        Get the name of the action this plugin handles.

        Returns:
            str: The action name (e.g. 'search', 'answer', 'reflect')
        """
        pass

    @abstractmethod
    def get_prompt_section(self, session: "ResearchSession") -> str:
        """
        Get the prompt section for this action.

        Args:
            session: The current research session

        Returns:
            str: The prompt section describing this action
        """
        pass

    @abstractmethod
    async def handle(self, session: "ResearchSession", current_question: str) -> bool:
        """
        Handle the action.

        Args:
            session: The current research session
            current_question: The current question being researched

        Returns:
            bool: True if the research should continue, False if it should stop
        """
        pass

    @handler_hook
    async def _handle(self, session: "ResearchSession", current_question: str) -> bool:
        return await self.handle(session, current_question)

    @abstractmethod
    def get_schema_properties(
        self, session: "ResearchSession"
    ) -> Optional[Dict[str, Any]]:
        """
        Get the schema properties for this action.

        Returns:
            Optional[Dict[str, Any]]: The schema properties, or None if not needed
        """
        pass

    def get_schema_required_fields(self, session: "ResearchSession") -> List[str]:
        """
        Get the required fields for this action's schema.

        Returns:
            List[str]: List of required field names
        """
        properties = self.get_schema_properties(session)
        if properties is None:
            return []
        return list(properties.keys())

    def is_available(self, session: "ResearchSession") -> bool:
        """
        Check if this action is available in the current session.

        Args:
            session: The current research session

        Returns:
            bool: True if the action is available, False otherwise
        """
        plugin_state = session.get_plugin_state(self.action_name)
        return plugin_state.enabled

    @property
    def max_attempts(self) -> int:
        """
        Get the maximum number of attempts for this action.
        """
        return 3

    def dump_plugin_context(self, session: "ResearchSession") -> None:
        """
        Dump the plugin's state to file system for debugging.

        if you want to dump the information to file system, create a custom file
        in session.context_store directory.

        Args:
            session: The current research session
        """
        pass

    def get_state(self, session: "ResearchSession") -> PluginState:
        """
        Get the plugin's state from the session.

        Args:
            session: The current research session

        Returns:
            PluginState: The plugin's state
        """
        return session.get_plugin_state(self.action_name)

    def update_state(self, session: "ResearchSession", data: Dict[str, Any]) -> None:
        """
        Update the plugin's state in the session.

        Args:
            session: The current research session
            data: The data to update the state with
        """
        state = self.get_state(session)
        state.update(data)

    def record_error(self, session: "ResearchSession", error: Exception) -> None:
        """
        Record an error in the plugin's state.

        Args:
            session: The current research session
            error: The error that occurred
        """
        state = self.get_state(session)
        state.record_error(error)

    def is_healthy(self, session: "ResearchSession") -> bool:
        """
        Check if the plugin is in a healthy state.

        Args:
            session: The current research session

        Returns:
            bool: True if the plugin is healthy, False otherwise
        """
        state = self.get_state(session)
        return state.is_healthy()

    def reset_state(self, session: "ResearchSession") -> None:
        """
        Reset the plugin's state in the session.

        Args:
            session: The current research session
        """
        state = self.get_state(session)
        state.reset()

    def get_recent_history(self, session: "ResearchSession", limit: int = 5) -> list:
        """
        Get the plugin's recent history.

        Args:
            session: The current research session
            limit: Maximum number of history entries to return

        Returns:
            list: Recent history entries
        """
        state = self.get_state(session)
        return state.get_recent_history(limit)

    def reset_attempts(self, session: "ResearchSession") -> None:
        """
        Reset the plugin's attempts in the session.

        Args:
            session: The current research session
        """
        state = self.get_state(session)
        state.error_count = 0

    def increase_bad_attempts(self, session: "ResearchSession") -> None:
        """
        Increase the plugin's bad attempts in the session.

        Args:
            session: The current research session
        """
        state = self.get_state(session)
        state.error_count += 1

    def has_exceeded_attempts(self, session: "ResearchSession") -> bool:
        """
        Check if the plugin has exceeded its maximum attempts.

        Args:
            session: The current research session

        Returns:
            bool: True if max attempts exceeded, False otherwise
        """
        state = self.get_state(session)
        return state.error_count >= self.max_attempts
