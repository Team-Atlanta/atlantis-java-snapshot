import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from libAgents.tools import AiderCoder
from aider.models import Model


os_env_patch = {
    "OPENAI_API_BASE": os.getenv("AIXCC_LITELLM_HOSTNAME"),
    "OPENAI_API_KEY": os.getenv("LITELLM_KEY"),
}


def test_aider_wrapper():
    with patch.dict(os.environ, os_env_patch):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_file.py"
            test_file.touch()  # Create empty test file

            coder = AiderCoder(
                main_model=Model("gpt-4.1-mini"),
                repo_path=temp_dir,
                fnames=[test_file],
                working_dir=temp_dir,
            )
            output = coder.run(
                "Write a function that prints 'Hello, world!' in test_file.py"
            )
            assert "Hello, world!" in output

            file_content = Path(test_file).read_text()
            assert "Hello, world!" in file_content
