import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Generator

import pytest

from libAgents.plugins.ask_codebase import AskCodebasePlugin, CodebaseKnowledge
from libAgents.base import PluginState, ENABLE_IN_NEXT_ROUND, DISABLE_IN_NEXT_ROUND
from libAgents.session import ResearchSession
from libAgents.base.registry import ActionRegistry


@pytest.fixture
def mock_session() -> Mock:
    """Create a mock research session for testing."""
    session = Mock(spec=ResearchSession)
    session.step = 1
    session.question = "Test question about codebase"
    session.override_model = None
    session.context_store = "./test_context"
    session.get_plugin_state.return_value = PluginState(enabled=True, data={})
    session.add_diary_entry = Mock()
    session.add_knowledge = Mock()
    return session


@pytest.fixture
def temp_src_dir() -> Generator[Path, None, None]:
    """Create a temporary source directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def temp_context_dir() -> Generator[str, None, None]:
    """Create a temporary directory for context storage."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def os_env_patch():
    """Environment variables patch for testing."""
    return {
        "OPENAI_BASE_URL": "https://test-api.openai.com",
        "OPENAI_API_KEY": "test-api-key",
        "LITELLM_KEY": "test-litellm-key",
        "AIXCC_LITELLM_HOSTNAME": "https://test-litellm.com",
    }


class TestAskCodebasePlugin:
    """Test suite for AskCodebasePlugin."""

    def test_plugin_initialization_default(self, temp_src_dir):
        """Test plugin initialization with default parameters."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        assert plugin.model_name is None
        assert plugin.project_name == "test_project"
        assert plugin.src_path == temp_src_dir
        assert plugin.codex is None
        assert plugin.action_name == "ask-codebase"

    def test_plugin_initialization_with_model(self, temp_src_dir):
        """Test plugin initialization with specific model."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir, model_name="gpt-4.1")
        assert plugin.model_name == "gpt-4.1"
        assert plugin.project_name == "test_project"
        assert plugin.src_path == temp_src_dir
        assert plugin.codex is None

    def test_schema_properties(self, mock_session, temp_src_dir):
        """Test that schema properties are correctly defined."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        schema = plugin.get_schema_properties(mock_session)

        assert "question" in schema
        assert schema["question"]["type"] == "string"
        assert "codebase" in schema["question"]["description"].lower()

    def test_prompt_section(self, mock_session, temp_src_dir):
        """Test that prompt section is correctly formatted."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        prompt = plugin.get_prompt_section(mock_session)

        assert "ask-codebase" in prompt
        assert "oracle" in prompt.lower()
        assert "codebase" in prompt.lower()

    @patch("libAgents.plugins.ask_codebase.get_model")
    def test_get_model_name_priority(self, mock_get_model, mock_session, temp_src_dir):
        """Test model name priority: instance > session > global."""
        mock_model = Mock()
        mock_model.model_name = "global-model"
        mock_get_model.return_value = mock_model

        # Test 1: Instance model takes priority
        plugin = AskCodebasePlugin(
            "test_project", temp_src_dir, model_name="instance-model"
        )
        model_name = plugin._get_model_name(mock_session)
        assert model_name == "instance-model"

        # Test 2: Session override takes priority over global
        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        mock_session.override_model = "session-model"
        model_name = plugin._get_model_name(mock_session)
        assert model_name == "session-model"

        # Test 3: Global model is used when no overrides
        mock_session.override_model = None
        model_name = plugin._get_model_name(mock_session)
        assert model_name == "global-model"

    @patch.dict(os.environ, {}, clear=True)
    @patch("libAgents.plugins.ask_codebase.get_model")
    def test_setup_api_credentials(self, mock_get_model, mock_session, temp_src_dir):
        """Test API credentials setup."""
        mock_model = Mock()
        mock_model.base_url = "https://test-api.com"
        mock_model.api_key = "test-key"
        mock_get_model.return_value = mock_model

        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        plugin._setup_api_credentials(mock_session)

        assert os.environ["OPENAI_BASE_URL"] == "https://test-api.com"
        assert os.environ["OPENAI_API_KEY"] == "test-key"

    @patch("libAgents.plugins.ask_codebase.OpenAICodex")
    @patch("libAgents.plugins.ask_codebase.get_model")
    def test_get_codex_initialization(
        self, mock_get_model, mock_codex_class, mock_session, temp_src_dir
    ):
        """Test codex initialization."""
        mock_model = Mock()
        mock_model.model_name = "test-model"
        mock_model.base_url = "https://test-api.com"
        mock_model.api_key = "test-key"
        mock_get_model.return_value = mock_model

        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        codex = plugin._get_codex(mock_session)

        # Verify codex was created
        assert plugin.codex is not None
        mock_codex_class.assert_called_once()

        # Verify subsequent calls return same instance
        codex2 = plugin._get_codex(mock_session)
        assert codex is codex2
        assert mock_codex_class.call_count == 1

    def test_add_codebase_knowledge(self, mock_session, temp_src_dir):
        """Test adding codebase knowledge to session."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)
        question = "What is the main function?"
        answer = "The main function is the entry point of the program."

        plugin.add_codebase_knowledge(mock_session, question, answer)

        # Verify add_knowledge was called with correct parameters
        mock_session.add_knowledge.assert_called_once()
        knowledge = mock_session.add_knowledge.call_args[0][0]

        assert isinstance(knowledge, CodebaseKnowledge)
        assert knowledge.question == question
        assert knowledge.answer == answer
        assert knowledge.source == "ask-codebase"
        assert knowledge.knowledge_type == "codebase_oracle"

    @pytest.mark.asyncio
    async def test_handle_success(self, mock_session, temp_src_dir):
        """Test successful handling of ask-codebase action."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)

        # Mock the codex directly on the plugin
        mock_codex = Mock()
        mock_codex.async_query = AsyncMock(return_value="This is the answer from codex")
        plugin.codex = mock_codex

        # Setup action parameters
        mock_session.get_action_param.return_value = "What is the main function?"

        # Execute handle
        result = await plugin.handle(mock_session, "Test question")

        # Verify result
        assert result == ENABLE_IN_NEXT_ROUND

        # Verify codex was called
        mock_codex.async_query.assert_called_once_with("What is the main function?")

        # Verify knowledge was added
        mock_session.add_knowledge.assert_called_once()

        # Verify diary entry was added
        mock_session.add_diary_entry.assert_called_once()
        diary_entry = mock_session.add_diary_entry.call_args[0][0]
        assert "ask-codebase" in diary_entry
        assert "What is the main function?" in diary_entry
        assert "This is the answer from codex" in diary_entry

    @pytest.mark.asyncio
    async def test_handle_no_question(self, mock_session, temp_src_dir):
        """Test handling when no question is provided."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)

        # Setup no question scenario
        mock_session.get_action_param.return_value = ""

        # Execute handle
        result = await plugin.handle(mock_session, "Test question")

        # Verify result
        assert result == ENABLE_IN_NEXT_ROUND

        # Verify diary entry indicates no question
        mock_session.add_diary_entry.assert_called_once()
        diary_entry = mock_session.add_diary_entry.call_args[0][0]
        assert "no question was provided" in diary_entry.lower()

    @pytest.mark.asyncio
    async def test_handle_empty_answer(self, mock_session, temp_src_dir):
        """Test handling when codex returns empty answer."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)

        # Mock the codex directly on the plugin
        mock_codex = Mock()
        mock_codex.async_query = AsyncMock(return_value="")
        plugin.codex = mock_codex

        # Setup action parameters
        mock_session.get_action_param.return_value = "What is the main function?"

        # Execute handle
        result = await plugin.handle(mock_session, "Test question")

        # Verify result
        assert result == ENABLE_IN_NEXT_ROUND

        # Verify no knowledge was added
        mock_session.add_knowledge.assert_not_called()

        # Verify diary entry indicates no answer
        mock_session.add_diary_entry.assert_called_once()
        diary_entry = mock_session.add_diary_entry.call_args[0][0]
        assert "did not provide any answer" in diary_entry.lower()

    @pytest.mark.asyncio
    async def test_handle_exception_in_codex(self, mock_session, temp_src_dir):
        """Test handling when codex raises an exception."""
        plugin = AskCodebasePlugin("test_project", temp_src_dir)

        # Mock the codex to raise an exception
        mock_codex = Mock()
        mock_codex.async_query = AsyncMock(side_effect=Exception("Codex error"))
        plugin.codex = mock_codex

        # Setup action parameters
        mock_session.get_action_param.return_value = "What is the main function?"

        # Execute handle
        result = await plugin.handle(mock_session, "Test question")

        # Verify result
        assert result == DISABLE_IN_NEXT_ROUND

        # Verify diary entry indicates error
        mock_session.add_diary_entry.assert_called_once()
        diary_entry = mock_session.add_diary_entry.call_args[0][0]
        assert "error" in diary_entry.lower()
        assert "Codex error" in diary_entry

    def test_codebase_knowledge_creation(self):
        """Test CodebaseKnowledge creation and methods."""
        knowledge = CodebaseKnowledge(
            source="ask-codebase",
            knowledge_type="codebase_oracle",
            question="What is the main function?",
            answer="The main function is the entry point.",
        )

        assert knowledge.knowledge_question() == "What is the main function?"
        assert knowledge.knowledge_answer() == "The main function is the entry point."
        assert knowledge.source == "ask-codebase"
        assert knowledge.knowledge_type == "codebase_oracle"

    @pytest.mark.asyncio
    async def test_integration_with_real_session(self, temp_context_dir, temp_src_dir):
        """Test integration with a real session (mocked codex)."""
        # Create real session
        registry = ActionRegistry()
        session = ResearchSession(
            question="Test question about codebase",
            token_budget=1000,
            plugin_registry=registry,
            context_saving_dir=temp_context_dir,
        )

        plugin = AskCodebasePlugin("test_project", temp_src_dir)

        # Mock codex
        mock_codex = Mock()
        mock_codex.async_query = AsyncMock(return_value="Test answer from codex")
        plugin.codex = mock_codex

        # Setup action details
        session.this_step = {
            "action": "ask-codebase",
            "action-details": {"question": "What is the main function?"},
        }

        # Execute handle
        result = await plugin.handle(session, "Test question")

        # Verify result
        assert result == ENABLE_IN_NEXT_ROUND

        # Verify knowledge was added to session
        knowledge_list = session.knowledge_manager.get_knowledge_by_type(
            "codebase_oracle"
        )
        assert len(knowledge_list) == 1
        assert knowledge_list[0].question == "What is the main function?"
        assert knowledge_list[0].answer == "Test answer from codex"

        # Verify diary entry was added
        assert len(session.diary_context) == 1
        assert "ask-codebase" in session.diary_context[0]
