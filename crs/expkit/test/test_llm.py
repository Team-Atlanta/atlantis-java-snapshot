#!/usr/bin/env python3

import json
import logging
import os
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from expkit.llm import LLMClient  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLLMClient(unittest.TestCase):
    """Simple tests for the LLMClient class."""

    def setUp(self):
        self.api_key = os.environ.get("LITELLM_KEY")
        self.base_url = os.environ.get("AIXCC_LITELLM_HOSTNAME")

        if not (self.api_key and self.base_url):
            self.skipTest(
                "LITELLM_KEY or AIXCC_LITELLM_HOSTNAME environment variables not set"
            )

    def test_basic_completion(self):
        """Test basic completion with a simple prompt."""
        try:
            client = LLMClient()

            result = client.completion(
                prompt="What is the capital of France?",
                # prompt="Which model you are?",
                model="openai/o3-mini",
                # model="claude-3-7-sonnet-20250219",
                # model="xai/grok-3-beta",
                # model="gemini/gemini-2.5-pro-preview-03-25",
                system_prompt="You are a helpful assistant that provides short, accurate answers.",
                temperature=0.7,
            )

            self.assertIsNotNone(result)
            self.assertIn("content", result)
            self.assertIsNotNone(result["content"])

            self.assertIn("Paris", result["content"])

            # Check usage statistics were updated
            self.assertGreater(client.total_tokens, 0)
            self.assertGreater(client.total_prompt_tokens, 0)
            self.assertGreater(client.total_completion_tokens, 0)
            self.assertEqual(client.request_count, 1)

            logger.info(f"Response: {result['content']}")
            logger.info(client.print_usage_stats())

        except Exception as e:
            self.fail(f"Basic completion test failed with exception: {str(e)}")

    def test_tool_calling(self):
        """Test completion with tool calling."""
        return
        try:
            client = LLMClient()

            # A simple weather tool
            weather_tool = {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            }
                        },
                        "required": ["location"],
                    },
                },
            }

            result = client.completion(
                prompt="What's the weather like in San Francisco?",
                model="gpt-4o",
                tools=[weather_tool],
                tool_choice="auto",
            )

            self.assertIsNotNone(result)

            self.assertIn("tool_calls", result)
            self.assertIsNotNone(result["tool_calls"])

            tool_calls = result["tool_calls"]
            self.assertEqual(len(tool_calls), 1)
            self.assertEqual(tool_calls[0].function.name, "get_weather")

            args = json.loads(tool_calls[0].function.arguments)
            self.assertIn("location", args)
            self.assertIn("San Francisco", args["location"])

            logger.info(
                f"Tool call: {tool_calls[0].function.name}({tool_calls[0].function.arguments})"
            )
            logger.info(client.print_usage_stats())

        except Exception as e:
            self.fail(f"Tool calling test failed with exception: {str(e)}")


if __name__ == "__main__":
    unittest.main()
