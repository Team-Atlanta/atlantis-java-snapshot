# [Team-Atlanta Fork] Anthropic API Proxy for Gemini & OpenAI Models

**Use Anthropic clients (like Claude Code) with Gemini or OpenAI backends.** 

A proxy server that lets you use Anthropic clients with Gemini or OpenAI models via LiteLLM.

## Quick Start

### Prerequisites

Setup lilellm key

```python3
LITELM_KEY = os.environ.get("LITELLM_KEY")
LITELM_URL = os.environ.get("AIXCC_LITELLM_HOSTNAME")
```

### Install

```bash
uv pip install .
```

### Run the proxy:
   ```bash
   # Using uv with uvicorn (useful for debugging)
   uv run uvicorn anthropic_proxy_server:app --host 0.0.0.0 --port 8082 --reload
   
   # Or directly with the built-in server (with command-line options)
   anthropic-proxy --port 8082 --provider openai
   ```
   Available command-line options:
   - `--port PORT`: Specify the port to run the server on (default: 8082)
   - `--provider {openai,anthropic,google}`: Specify the preferred provider

### Using with Claude Code

1. **Install Claude Code** (if you haven't already):
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Connect to your proxy**:
   ```bash
   ANTHROPIC_BASE_URL=http://localhost:8082 claude
   ```