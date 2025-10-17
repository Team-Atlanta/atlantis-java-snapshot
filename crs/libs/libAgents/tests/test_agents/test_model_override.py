import pytest

from libAgents.agents import DeepSearchAgent


@pytest.mark.parametrize(
    "model_name",
    [
        "grok-3-mini",
        "gpt-4.1-mini",
        "gemini-2.5-flash-preview-05-20",
    ],
)
@pytest.mark.asyncio
async def test_various_models_parameterized(model_name):
    agent = DeepSearchAgent()
    result = await agent.query(
        "What is the capital of France?", override_model=model_name
    )
    assert result is not None
    assert "Paris" in result
