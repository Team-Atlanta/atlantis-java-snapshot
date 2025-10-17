import asyncio
import logging
import argparse

from libAgents.agents import DeepSearchAgent

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("libAgents").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# example.py


async def main():
    parser = argparse.ArgumentParser(
        description="Run DeepSearchAgent with specified model"
    )
    parser.add_argument(
        "--model",
        default="gemini",
        help="Model name to use for the query (default: gpt)",
    )
    args = parser.parse_args()

    if args.model == "gpt":
        model = "gpt-4.1"
    elif args.model == "gemini":
        model = "gemini-2.5-pro"
    elif args.model == "claude":
        model = "claude-opus-4-20250514"
    else:
        raise ValueError(f"Invalid model: {args.model}")

    agent = DeepSearchAgent(enable_context_saving=True)

    logger.info(f"Running with {model}")
    result = await agent.query("Who is Andrew Chi-Chih Yao?", model)

    print(f"\n>>> {model} Answer:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
