import pytest
from libAgents.model import generate_text, generate_object, ResponseWrapper
from libAgents.config import get_model
import json


@pytest.mark.asyncio
async def test_generate_text_simple_prompt():
    model = get_model("test", override_model="claude-opus-4-20250514")

    # Test with simple prompt
    result = await generate_text(
        model=model,
        prompt="Say 'Hello, this is a test response' and nothing else.",
        temperature=0.1,  # Low temperature for consistent output
    )

    # Verify the result structure
    assert isinstance(result, ResponseWrapper)
    assert isinstance(result.object, str)
    assert len(result.object) > 0

    # Check that the response contains expected content
    assert "Hello, this is a test response" in result.object

    print(f"Response: {result.object}")
    print(f"Usage: {result.usage}")


@pytest.mark.asyncio
async def test_generate_object_with_anyof_schema():
    """Test generate_object with claude-4-opus using a schema with anyOf."""
    model = get_model("test", override_model="claude-opus-4-20250514")

    # Define a schema with anyOf for a flexible response type
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the item"},
            "value": {
                "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "boolean"}],
                "description": "Value can be string, number, or boolean",
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "priority": {
                        "anyOf": [
                            {"type": "string", "enum": ["low", "medium", "high"]},
                            {"type": "integer", "minimum": 1, "maximum": 10},
                        ],
                        "description": "Priority as either a string (low/medium/high) or number (1-10)",
                    },
                },
                "required": ["category"],
            },
        },
        "required": ["name", "value", "metadata"],
    }

    # Test prompt that should generate varied response types
    prompt = """Generate a JSON object for a configuration item with:
    - name: "api_timeout"
    - value: 30 (as a number)
    - metadata with category: "performance", tags: ["api", "timeout"], and priority: "high" """

    result = await generate_object(
        model=model, schema=schema, prompt=prompt, temperature=0.1
    )

    # Verify the result structure
    assert isinstance(result, ResponseWrapper)
    assert isinstance(result.object, str)

    # Parse the JSON response
    parsed = json.loads(result.object)

    # Verify the response matches our schema
    assert "name" in parsed
    assert parsed["name"] == "api_timeout"

    assert "value" in parsed
    assert parsed["value"] == 30  # Should be a number

    assert "metadata" in parsed
    assert parsed["metadata"]["category"] == "performance"
    assert "tags" in parsed["metadata"]
    assert "api" in parsed["metadata"]["tags"]
    assert "timeout" in parsed["metadata"]["tags"]
    assert parsed["metadata"]["priority"] == "high"  # Should be string in this case

    print(f"Generated object: {json.dumps(parsed, indent=2)}")
    print(f"Usage: {result.usage}")
