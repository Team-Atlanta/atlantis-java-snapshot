import asyncio
import logging
from pathlib import Path
import tempfile
from libAgents.agents import DeepSearchAgent
from libAgents.plugins import AnswerPlugin, ReflectPlugin, CoderPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)

model_names = [
    # "o4-mini",
    # "gpt-4.1",
    "gemini-2.5-pro",
    # "claude-3-7-sonnet-20250219",
    # "claude-opus-4-20250514",
]


async def run_all_simple_coding():
    temp_dir_obj = tempfile.TemporaryDirectory()  # Use context manager
    temp_dir = temp_dir_obj.name
    # It might be better to instantiate the agent once if possible,
    # but CoderPlugin takes model_name, so we might need it inside the loop.
    # Let's keep agent creation inside for now.

    results = {}
    for model_name in model_names:
        print(f"\n--- Running for model: {model_name} ---")
        # Assuming agent can be reused or recreated safely within the same loop
        agent = DeepSearchAgent(
            plugins=[
                AnswerPlugin(),
                CoderPlugin(
                    model_name=model_name,
                    project_name=f"test_project_{model_name}",  # Avoid name conflicts
                    main_repo=Path(temp_dir),  # Separate dirs
                ),
                ReflectPlugin(),
            ]
        )
        try:
            # Ensure the agent query and potential internal cleanup happens here
            result = await agent.query(
                "Show me a python program for the fastest way to calculate the minimum spanning tree (MST) of a graph"
            )
            print("Answer:\n")
            print(result)
            results[model_name] = result
        except Exception as e:
            print(f"Error querying agent with {model_name}: {e}")
            results[model_name] = {"error": str(e)}
            raise e
    # Cleanup temp dir after all runs are complete
    temp_dir_obj.cleanup()
    return results


if __name__ == "__main__":
    asyncio.run(run_all_simple_coding())
