import asyncio
import logging

from libAgents.agents import DeepSearchAgent
from libAgents.plugins import AnswerPlugin, FsReaderPlugin, ReflectPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)

agent = DeepSearchAgent(plugins=[AnswerPlugin(), FsReaderPlugin(), ReflectPlugin()])

result = asyncio.run(
    agent.query("What is the content of the file /etc/passwd in local filesystem ?")
)

print("Answer:\n")
print(result)
