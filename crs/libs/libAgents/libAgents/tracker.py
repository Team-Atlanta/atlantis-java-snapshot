import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# A simple Python implementation of an EventEmitter.
class EventEmitter:
    def __init__(self):
        self._events: Dict[str, List[Callable[..., None]]] = {}

    def on(self, event: str, listener: Callable[..., None]) -> None:
        """Register an event listener for the specified event."""
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(listener)

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event and call all registered listeners."""
        for listener in self._events.get(event, []):
            listener(*args, **kwargs)


# ---------------------------
# ActionTracker
# ---------------------------


class ActionTracker(EventEmitter):
    def __init__(self):
        super().__init__()
        # Initial state with default values.
        self.state: Dict[str, Any] = {
            "thisStep": {
                "action": "answer",
                "answer": "",
                "thoughts": "",
            },
            "gaps": [],
            "totalStep": 0,
        }

    def track_action(self, new_state: Dict[str, Any]) -> None:
        """
        Update the state by merging the new_state into the existing state,
        then emit an 'action' event with the updated state.
        """
        self.state = {**self.state, **new_state}
        self.emit("action", self.state)

    def get_state(self) -> Dict[str, Any]:
        """
        Return a shallow copy of the current state.
        """
        return self.state.copy()

    def reset(self) -> None:
        """
        Reset the tracker to its initial state.
        """
        self.state = {
            "thisStep": {
                "action": "answer",
                "answer": "",
                "thoughts": "",
            },
            "gaps": [],
            "totalStep": 0,
        }


# ---------------------------
# TokenTracker
# ---------------------------


def console_error(message: str) -> None:
    logger.error(f"\x1b[31m{message}\x1b[0m")


class TokenTracker(EventEmitter):
    def __init__(self, budget: Optional[int] = None):
        """
        :param budget: Optional integer representing the maximum allowed tokens.
        """
        super().__init__()
        self.usages: List[Dict[str, int]] = []
        self.budget = budget  # token budget for the current research session

    def track_usage(self, tool: str, tokens: int) -> None:
        """
        Track token usage for a given tool.
        If the token budget is exceeded, logs error and raises ValueError.
        Otherwise, the usage is recorded and a 'usage' event is emitted.
        """
        current_total = self.get_total_usage()
        if self.budget is not None and current_total + tokens > self.budget:
            # Log error message first (won't stop execution)
            error_msg = (
                f"\n[TokenBudgetError] Token budget exceeded!\n"
                f"  Current usage: {current_total:,} tokens\n"
                f"  Attempted to add: {tokens:,} tokens\n"
                f"  Budget limit: {self.budget:,} tokens\n"
                f"  Exceeds by: {(current_total + tokens - self.budget):,} tokens\n"
            )
            console_error(error_msg)
            # Then raise the error to stop execution
            # raise ValueError(f"Token budget exceeded: {current_total + tokens} > {self.budget}")

        self.usages.append({"tool": tool, "tokens": tokens})
        self.emit("usage", {"tool": tool, "tokens": tokens})

    def get_total_usage(self) -> int:
        """
        Calculate and return the total number of tokens used.
        """
        return sum(usage["tokens"] for usage in self.usages)

    def get_usage_breakdown(self) -> Dict[str, int]:
        """
        Return a breakdown of token usage per tool.
        """
        breakdown: Dict[str, int] = {}
        for usage in self.usages:
            tool = usage["tool"]
            breakdown[tool] = breakdown.get(tool, 0) + usage["tokens"]
        return breakdown

    def print_summary(self) -> None:
        """
        Print a summary of the token usage, including the total and a breakdown per tool.
        """
        breakdown = self.get_usage_breakdown()
        print(
            "Token Usage Summary:",
            {
                "total": self.get_total_usage(),
                "breakdown": breakdown,
            },
        )

    def reset(self) -> None:
        """
        Reset the token usage tracker.
        """
        self.usages = []


# ---------------------------
# Example Usage
# ---------------------------
if __name__ == "__main__":
    # Example: ActionTracker
    def on_action(state):
        print("Action event emitted with state:", state)

    action_tracker = ActionTracker()
    action_tracker.on("action", on_action)
    action_tracker.track_action({"gaps": ["missing info"], "badAttempts": 1})
    print("Current ActionTracker state:", action_tracker.get_state())
    action_tracker.reset()
    print("State after reset:", action_tracker.get_state())

    # Example: TokenTracker
    def on_usage(usage):
        print("Usage event emitted:", usage)

    token_tracker = TokenTracker(budget=100)
    token_tracker.on("usage", on_usage)
    token_tracker.track_usage("toolA", 30)
    token_tracker.track_usage("toolB", 40)
    print("Total tokens used:", token_tracker.get_total_usage())
    token_tracker.print_summary()

    try:
        token_tracker.track_usage("toolC", 50)  # This should exceed the budget.
    except ValueError as e:
        print("Error:", e)
