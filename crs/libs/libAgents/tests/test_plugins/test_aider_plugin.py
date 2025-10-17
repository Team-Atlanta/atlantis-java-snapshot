import tempfile
import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

from libAgents.plugins import CoderPlugin
from libAgents.base import PluginState


os_env_patch = {
    "OPENAI_API_BASE": os.getenv("AIXCC_LITELLM_HOSTNAME"),
    "OPENAI_API_KEY": os.getenv("LITELLM_KEY"),
}


@pytest.mark.asyncio
async def test_write_script_42():
    with patch.dict(os.environ, os_env_patch):
        mock_session = Mock()
        action_details = {
            "coding_task": "Write a simple function that returns 42",
            "script_name": "test_script.py",
            "context_files": [],
        }
        mock_session.get_action_details.return_value = action_details

        # Create a real temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up session's context_store
            temp_dir_path = Path(temp_dir)
            mock_session.context_store = temp_dir_path
            mock_session.override_model = None

            # Create an empty test script file
            test_script_path = temp_dir_path / "test_script.py"
            with open(test_script_path, "w") as f:
                f.write("# Test file for Aider to modify\n")

            # Create plugin instance
            plugin = CoderPlugin(
                project_name="test_project",
                main_repo=temp_dir,
            )

            # Set working_dir attribute - by default it would be main_repo
            plugin.working_dir = temp_dir

            # Setup plugin state
            mock_session.get_plugin_state.return_value = PluginState(
                enabled=True, data={}
            )

            await plugin.handle(mock_session, "Implement a function")

            # Verify the script file exists
            assert test_script_path.exists()

            # Verify the content has been modified
            content = test_script_path.read_text()
            assert "42" in content
            print(content)
            assert (
                len(content) > 20
            )  # Should have more content than our initial comment


@pytest.mark.asyncio
async def test_writing_corpus_generator():
    with patch.dict(os.environ, os_env_patch):
        pass
