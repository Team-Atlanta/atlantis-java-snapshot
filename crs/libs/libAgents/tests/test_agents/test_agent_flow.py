import asyncio
import pytest
from libAgents.agents import AgentBase
from typing import override


class FetchData(AgentBase):
    @override
    async def run(self, input_data):
        return {"data": [1, 2, 3]}


class Multiply(AgentBase):
    @override
    async def run(self, input_data):
        factor = self.data.get("factor", 1)
        return [x * factor for x in input_data["data"]]


class ToString(AgentBase):
    @override
    async def run(self, input_data):
        return ", ".join(map(str, input_data))


class Print(AgentBase):
    @override
    async def run(self, input_data):
        print(input_data)
        return input_data


@pytest.mark.asyncio
def test_agent_flow():
    head = FetchData()
    head >> Multiply(factor=10) >> ToString() >> Print()
    res = asyncio.run(head.start())
    assert res == "10, 20, 30"
