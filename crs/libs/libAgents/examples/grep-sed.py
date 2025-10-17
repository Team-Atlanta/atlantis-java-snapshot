import asyncio
import logging

from libAgents.agents import DeepSearchAgent
from libAgents.plugins import AnswerPlugin, SedPlugin, ReflectPlugin, RipGrepPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)

agent = DeepSearchAgent(
    plugins=[
        AnswerPlugin(),
        ReflectPlugin(),
        RipGrepPlugin(),
        SedPlugin(),
    ]
)

result = asyncio.run(
    agent.query(
        "What file has the source code of the AnswerPlugin? Show me the related code snippets."
    )
)

print("Answer:\n")
print(result)
