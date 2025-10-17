import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from libAgents.agents.deep_search_agent import DeepSearchAgent
from libAgents.base import ActionPlugin, ENABLE_IN_NEXT_ROUND, DISABLE_IN_NEXT_ROUND
from libAgents.base.registry import ActionRegistry
from libAgents.session import ResearchSession

ENABLED = True
DISABLED = False


class MockPlugin(ActionPlugin):
    """Mock plugin for testing state transitions."""

    def __init__(self, name, behavior=ENABLE_IN_NEXT_ROUND):
        self._name = name
        self._behavior = behavior
        self.handle_called = 0

    @property
    def action_name(self):
        return self._name

    def get_prompt_section(self, session):
        return (
            f"<action-{self._name}>\nTest action {self._name}\n</action-{self._name}>"
        )

    async def handle(self, session, current_question):
        print("PLUGIN HANDLE: ", self._name)
        self.handle_called += 1
        return self._behavior

    def get_schema_properties(self, _session: ResearchSession):
        return {
            f"{self._name}_data": {
                "type": "string",
                "description": f"Test data for {self._name}",
            }
        }

    def is_available(self, session):
        # Override to use parent's implementation
        return super().is_available(session)


class TestSessionDeepSearchAgent(DeepSearchAgent):
    """Extended agent class that stores the session for testing purposes."""

    async def query(self, question: str, token_budget: int = 500_000):
        """Override query to store the session for testing."""
        session = ResearchSession(
            question=question,
            token_budget=token_budget,
            plugin_registry=self.registry,
            context_saving_dir=self.context_saving_dir,
        )
        self.last_session = session

        # Main processing loop (copied from parent with session storage)
        while session.should_continue():
            session.next_step()
            current_question = session.get_current_question()

            prompt = session.get_prompt()

            try:
                available_plugins = [
                    plugin
                    for plugin in self.registry.get_plugins()
                    if plugin.is_available(session)
                ]

                await self._generate_next_action(session, prompt, available_plugins)
                action = session.this_step.get("action")
                if action:
                    plugin = self.registry.get_plugin(action)
                    if plugin and plugin.is_available(session):
                        await plugin._handle(session, current_question)

                # Store context for debugging
                if self.enable_context_saving:
                    await session.save_context(prompt, session.total_step)

                if session.is_answered:
                    break

            except Exception:
                # Handle errors
                if self.enable_context_saving:
                    await session.save_context(prompt, session.total_step)
                break

        session.is_answered = True

        return {
            "result": session.get_action_details(),
            "context": session.get_context(),
            "session": session,
        }

    async def _generate_next_action(self, session, prompt, available_plugins):
        """Helper method to generate the next action."""
        result = await self._get_model_response(prompt, available_plugins)
        session.this_step = result
        return result

    async def _get_model_response(self, prompt, available_plugins):
        """Patched in tests to return mock responses."""
        from libAgents.config import get_model
        from libAgents.model import generate_object

        result = await generate_object(
            model=get_model("agent"),
            schema=self.registry.get_schema_from_plugins(
                self.last_session, available_plugins
            ),
            prompt=prompt,
            temperature=1,
        )
        import json

        return json.loads(result.object)


@pytest.mark.asyncio
async def test_plugin_state_transitions():
    """Test that plugin state transitions work as expected with the handler_hook decorator."""

    # Create plugins with different behaviors
    always_enabled_plugin = MockPlugin("always_enabled", ENABLE_IN_NEXT_ROUND)
    always_disabled_plugin = MockPlugin("always_disabled", DISABLE_IN_NEXT_ROUND)
    toggling_plugin = MockPlugin("toggling")  # Default is ENABLE

    # Create agent with the test plugins
    agent = TestSessionDeepSearchAgent(
        plugins=[always_enabled_plugin, always_disabled_plugin, toggling_plugin],
        enable_context_saving=False,
    )

    # Mock the generate_object function to control the "AI" response
    with patch("libAgents.model.generate_object") as mock_generate:
        # Sequence of actions to test state transitions
        actions = [
            {
                "action": "always_enabled",
                "thoughts": "Testing always enabled plugin",
                "action-details": {
                    "always_enabled_data": "test",
                },
            },
            {
                "action": "toggling",
                "thoughts": "Testing toggling plugin",
                "action-details": {
                    "toggling_data": "test",
                },
            },
            {
                "action": "always_enabled",
                "thoughts": "Testing always enabled plugin again",
                "action-details": {
                    "always_enabled_data": "test2",
                },
            },
            {
                "action": "always_disabled",
                "thoughts": "Testing always disabled plugin",
                "action-details": {
                    "always_disabled_data": "test",
                },
            },
        ]

        # Set up the mock to return each action in sequence
        mock_responses = []
        for action in actions:
            mock_response = MagicMock()
            mock_response.object = str(action).replace("'", '"')
            mock_response.usage.total_tokens = 100
            mock_responses.append(mock_response)

        mock_generate.side_effect = mock_responses

        # Run the query
        await agent.query("Test question", token_budget=10000)

        # Verify the plugins were called in the expected order
        assert always_enabled_plugin.handle_called == 2  # Called in steps 1 and 4
        assert always_disabled_plugin.handle_called == 1  # Called in step 2
        assert toggling_plugin.handle_called == 1  # Called in step 3

        # Check the session state after running
        session = agent.last_session

        assert session.get_plugin_state("always_enabled").enabled == ENABLED
        assert session.get_plugin_state("toggling").enabled == ENABLED
        # disable the current but enable all of the others
        assert session.get_plugin_state("always_disabled").enabled == DISABLED


@pytest.mark.asyncio
async def test_handler_hook_error_handling():
    """Test that plugin state is properly handled after an error in plugin.handle."""

    # Create a plugin that raises an exception
    error_plugin = MockPlugin("error_plugin")
    error_plugin.handle = AsyncMock(side_effect=Exception("Test error"))

    # Create a session directly instead of using the agent
    registry = ActionRegistry()
    registry.register(error_plugin)

    session = ResearchSession(
        question="Test error handling",
        token_budget=1000,
        plugin_registry=registry,
        context_saving_dir="./context_store",
    )

    # Get the plugin and manually call _handle (which uses handler_hook)
    plugin = registry.get_plugin("error_plugin")
    current_question = "Test question"

    # Set this_step for context update
    session.this_step = {
        "action": "error_plugin",
        "thoughts": "Testing error handling",
        "action-details": {
            "error_plugin_data": "test",
        },
    }

    # Call the wrapped handle method directly
    result = await plugin._handle(session, current_question)

    # The result should be False (because handler_hook returns False on error)
    assert result == DISABLE_IN_NEXT_ROUND


@pytest.mark.asyncio
async def test_error_plugin_state_after_error():
    """Test that the error plugin state is properly handled after an error in plugin.handle."""

    # Create a plugin that raises an exception
    error_plugin = MockPlugin("error_plugin")
    error_plugin.handle = AsyncMock(side_effect=Exception("Test error"))

    with patch("libAgents.model.generate_object") as mock_generate:
        mock_response = MagicMock()
        mock_response.object = '{"action": "error_plugin", "thoughts": "Testing error", "action-details": {"error_plugin_data": "test"}}'
        mock_response.usage.total_tokens = 100
        mock_generate.return_value = mock_response

    agent = TestSessionDeepSearchAgent(
        plugins=[error_plugin], enable_context_saving=False
    )

    await agent.query("Test error handling", token_budget=1000)

    session = agent.last_session
    assert session.get_plugin_state("error_plugin").enabled == DISABLED


@pytest.mark.asyncio
async def test_handler_hook_enable_all_plugins_behavior():
    """
    Test that the handler_hook correctly re-enables all plugins before
    setting the active plugin's state based on its return value.
    """

    # Create a test plugin that will manipulate other plugins
    class StateMutatingPlugin(MockPlugin):
        async def handle(self, session, current_question):
            print("STATE MUTATOR HANDLE")
            self.handle_called += 1

            # First disable all plugins
            for plugin_name in ["plugin_a", "plugin_b", "plugin_c", "mutator"]:
                session.disable_plugin(plugin_name)

            # Then verify they're all disabled
            for plugin_name in ["plugin_a", "plugin_b", "plugin_c", "mutator"]:
                assert session.get_plugin_state(plugin_name).enabled == DISABLED

            # Return value will determine if this plugin stays enabled
            print("STATE MUTATOR RETURN")
            # heuristic: if the mutator is called, we assume the answer is found
            session.is_answered = True
            return self._behavior

    print("SCENARIO 1")
    # Create plugins - one mutating plugin and three regular plugins
    plugin_a = MockPlugin("plugin_a")
    plugin_b = MockPlugin("plugin_b")
    plugin_c = MockPlugin("plugin_c")

    # SCENARIO 1: Test with ENABLE_IN_NEXT_ROUND
    mutator = StateMutatingPlugin("mutator", ENABLE_IN_NEXT_ROUND)  # Enable itself

    # Create agent
    agent = TestSessionDeepSearchAgent(
        plugins=[plugin_a, plugin_b, plugin_c, mutator], enable_context_saving=False
    )

    # Mock the generate_object function to select the mutator
    with patch("libAgents.model.generate_object") as mock_generate:
        mock_response = MagicMock()
        mock_response.object = '{"action": "mutator", "thoughts": "Testing state manipulation", "action-details": {"mutator_data": "test"}}'
        mock_response.usage.total_tokens = 999
        mock_generate.return_value = mock_response

        # Run the query
        await agent.query("Test handler_hook behavior", token_budget=1000)

        # Verify the mutator was called
        assert mutator.handle_called == 1

        # Get session
        session = agent.last_session

        # After handler_hook executes, all plugins should be re-enabled
        # and then "mutator" should remain enabled due to its return value
        assert session.get_plugin_state("plugin_a").enabled == ENABLED
        assert session.get_plugin_state("plugin_b").enabled == ENABLED
        assert session.get_plugin_state("plugin_c").enabled == ENABLED
        assert session.get_plugin_state("mutator").enabled == ENABLED

    print("SCENARIO 2")
    # SCENARIO 2: Test with DISABLE_IN_NEXT_ROUND
    # Create a new agent with a mutator that returns DISABLE_IN_NEXT_ROUND
    mutator_disable = StateMutatingPlugin("mutator", DISABLE_IN_NEXT_ROUND)

    agent_disable = TestSessionDeepSearchAgent(
        plugins=[plugin_a, plugin_b, plugin_c, mutator_disable],
        enable_context_saving=False,
    )

    # Mock the generate_object function to select the mutator
    with patch("libAgents.model.generate_object") as mock_generate:
        mock_response = MagicMock()
        mock_response.object = '{"action": "mutator", "thoughts": "Testing state manipulation", "action-details": {"mutator_data": "test"}}'
        mock_response.usage.total_tokens = 100
        mock_generate.return_value = mock_response

        # Run the query
        await agent_disable.query(
            "Test handler_hook behavior with disable", token_budget=1000
        )

        # Verify the mutator was called
        assert mutator_disable.handle_called == 1

        # Get session
        session = agent_disable.last_session

        # Now all plugins should be enabled except the mutator
        assert session.get_plugin_state("plugin_a").enabled == ENABLED
        assert session.get_plugin_state("plugin_b").enabled == ENABLED
        assert session.get_plugin_state("plugin_c").enabled == ENABLED
        assert session.get_plugin_state("mutator").enabled == DISABLED


@pytest.mark.asyncio
async def test_complex_state_machine_transitions():
    """
    Test a complex state machine scenario where plugins interact with each other
    across multiple steps in the DeepSearchAgent's execution.
    """

    # Create custom plugin classes with specific behaviors
    class PingPlugin(MockPlugin):
        """Plugin that enables pong and disables itself."""

        async def handle(self, session, current_question):
            self.handle_called += 1
            # Enable the pong plugin
            session.enable_plugin("pong")
            # Return DISABLE to disable itself after execution
            return DISABLE_IN_NEXT_ROUND

    class PongPlugin(MockPlugin):
        """Plugin that enables ping and disables itself."""

        async def handle(self, session, current_question):
            self.handle_called += 1
            # Enable the ping plugin
            session.enable_plugin("ping")
            # Return DISABLE to disable itself after execution
            return DISABLE_IN_NEXT_ROUND

    class SwitcherPlugin(MockPlugin):
        """Plugin that toggles all plugins' states."""

        async def handle(self, session, current_question):
            self.handle_called += 1

            # Toggle all plugins (including self)
            for plugin_name in ["ping", "pong", "switcher", "terminator"]:
                current_state = session.get_plugin_state(plugin_name).enabled
                if current_state:
                    session.disable_plugin(plugin_name)
                else:
                    session.enable_plugin(plugin_name)

            # Always stay enabled so it can be called again
            return ENABLE_IN_NEXT_ROUND

    class TerminatorPlugin(MockPlugin):
        """Plugin that ends the session by setting is_answered."""

        async def handle(self, session, current_question):
            self.handle_called += 1
            # Mark the session as answered to stop the loop
            session.is_answered = True
            return ENABLE_IN_NEXT_ROUND

    # Create instances of the plugins
    ping = PingPlugin("ping")
    pong = PongPlugin("pong")
    switcher = SwitcherPlugin("switcher")
    terminator = TerminatorPlugin("terminator")

    # Create the agent with our plugins
    agent = TestSessionDeepSearchAgent(
        plugins=[ping, pong, switcher, terminator], enable_context_saving=False
    )

    # Set up the mock to return a sequence of actions
    with patch("libAgents.model.generate_object") as mock_generate:
        # Define the planned sequence: ping -> pong -> switcher -> ping -> terminator
        action_sequence = [
            {
                "action": "ping",
                "thoughts": "Start with ping",
                "action-details": {"ping_data": "test"},
            },
            {
                "action": "pong",
                "thoughts": "Then pong",
                "action-details": {"pong_data": "test"},
            },
            {
                "action": "switcher",
                "thoughts": "Now switch states",
                "action-details": {"switcher_data": "test"},
            },
            {
                "action": "ping",
                "thoughts": "Back to ping",
                "action-details": {"ping_data": "test2"},
            },
            {
                "action": "terminator",
                "thoughts": "End the test",
                "action-details": {"terminator_data": "test"},
            },
        ]

        # Create mock responses
        mock_responses = []
        for action in action_sequence:
            mock_response = MagicMock()
            mock_response.object = str(action).replace("'", '"')
            mock_response.usage.total_tokens = 100
            mock_responses.append(mock_response)

        mock_generate.side_effect = mock_responses

        # Run the query
        await agent.query("Test complex state machine", token_budget=10000)

        # Get the final session
        session = agent.last_session

        # Verify the plugins were called the expected number of times
        assert ping.handle_called == 2  # Called in steps 1 and 4
        assert pong.handle_called == 1  # Called in step 2
        assert switcher.handle_called == 1  # Called in step 3
        assert terminator.handle_called == 1  # Called in step 5

        # Verify the final state of each plugin
        # ping was disabled after its last call
        assert session.get_plugin_state("ping").enabled == ENABLED
        # pong was disabled after its call
        assert session.get_plugin_state("pong").enabled == ENABLED
        # switcher always stays enabled
        assert session.get_plugin_state("switcher").enabled == ENABLED
        # terminator stays enabled after its call
        assert session.get_plugin_state("terminator").enabled == ENABLED

        # Verify the session was properly marked as answered
        assert session.is_answered
