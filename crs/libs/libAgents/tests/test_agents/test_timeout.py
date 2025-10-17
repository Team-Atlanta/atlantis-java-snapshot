import asyncio
import pytest

from unittest.mock import patch, AsyncMock
from libAgents.agents import DeepSearchAgent


@pytest.mark.asyncio
async def test_timeout():
    with (
        patch(
            "libAgents.agents.deep_search_agent.DeepSearchAgent._query",
            new_callable=AsyncMock,
        ) as mock_internal_query,
        patch.object(
            DeepSearchAgent, "_handle_beast_mode", new_callable=AsyncMock
        ) as mock_beast_mode,
    ):

        async def side_effect(*args, **kwargs):
            await asyncio.sleep(3)
            return "Should not return this"

        mock_internal_query.side_effect = side_effect
        mock_beast_mode.return_value = (False, None)

        agent = DeepSearchAgent()
        result = await agent.query("What is the capital of France?", timeout=1)

        assert result is None
        mock_internal_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_timeout():
    with patch(
        "libAgents.agents.deep_search_agent.DeepSearchAgent._query",
        new_callable=AsyncMock,
    ) as mock_internal_query:

        async def side_effect(*args, **kwargs):
            await asyncio.sleep(3)
            return {"result": {"answer": "Should return this"}}

        mock_internal_query.side_effect = side_effect

        agent = DeepSearchAgent()
        result = await agent.query("What is the capital of France?", timeout=100)

        assert result == "Should return this"
        mock_internal_query.assert_awaited_once()
