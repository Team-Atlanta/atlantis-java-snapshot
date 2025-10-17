import pytest
from libAgents.tools import OpenAICodex, OpenAICodexConfig


@pytest.mark.asyncio
async def test_codex_tool():
    # codex --dangerously-auto-approve-everything "create a hello world python script"
    config = OpenAICodexConfig(model_name="gemini-2.5-pro", verbose=True)
    codex = OpenAICodex(config)
    code = await codex.async_query("Show the quick summary of the codebase")
    print(code)
