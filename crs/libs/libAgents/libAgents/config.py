import json
import logging
import os
import contextvars

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# --- Load configuration from config.json ---
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config_json = json.load(f)

# --- Types and Constants ---

# LLMProvider is either 'openai' or 'gemini'
LLM_PROVIDER_TYPE = ("openai", "gemini", "litellm")

# --- Environment Setup ---

# Copy the env section from config_json
env = config_json.get("env", {}).copy()

# Override config values with environment variables if present
for key in env.keys():
    if os.environ.get(key):
        env[key] = os.environ.get(key)

# --- Setup Proxy if Present ---
if env.get("https_proxy"):
    try:
        proxy_url = env["https_proxy"]
        # In Python you can use proxies with libraries like requests or httpx.
        # For example, with requests:
        # proxies = {"https": proxy_url}
        # Then pass proxies=proxies when making requests.
        logging.info("Using proxy: %s", proxy_url)
        # (Optional) Set your HTTP client's global proxy here if needed.
    except Exception as error:
        logging.error("Failed to set proxy: %s", error)

OPENAI_BASE_URL = env.get("OPENAI_BASE_URL")
LITELLEM_BASE_URL = env.get("AIXCC_LITELLM_HOSTNAME")
LITELLEM_KEY = env.get("LITELLM_KEY")
GEMINI_API_KEY = env.get("GEMINI_API_KEY")
OPENAI_API_KEY = env.get("OPENAI_API_KEY")
# os.environ["ANTHROPIC_API_KEY"] = LITELLEM_KEY
# os.environ["ANTHROPIC_API_BASE"] = LITELLEM_BASE_URL

RESONING_EFFORTS = {
    "grok-3-mini": "high",
    "o4-mini": "high",
    "claude-opus-4": "high",
}

# --- Context Variable for Model Override ---
# This allows setting a specific model per execution context (thread/async task)
# without changing function signatures.
default_model_override: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "default_model_override", default=None
)


# --- Determine LLM Provider ---
def is_valid_provider(provider: str) -> bool:
    return provider in LLM_PROVIDER_TYPE


LLM_PROVIDER = os.environ.get("LLM_PROVIDER") or config_json["defaults"]["llm_provider"]
if not is_valid_provider(LLM_PROVIDER):
    raise ValueError(f"Invalid LLM provider: {LLM_PROVIDER}")


# --- Tool Configuration Functions ---
def get_tool_config(tool_name: str, override_model: str | None = None) -> dict:
    """
    Returns a dictionary with keys:
      - model: string (the model name to use)
      - temperature: number
    """
    provider_config = config_json["models"][LLM_PROVIDER]
    default_config = provider_config["default"]
    tool_overrides = provider_config["tools"].get(tool_name, {})  # May be an empty dict

    # Determine the model name: ContextVar > Env Var > Config Default
    context_model = default_model_override.get()  # Read from context
    env_model = os.environ.get("DEFAULT_MODEL_NAME")
    config_default_model = default_config["model"]

    final_model = context_model or env_model or config_default_model
    if override_model is not None:
        final_model = override_model

    return {
        "model": final_model,
        "temperature": tool_overrides.get("temperature", default_config["temperature"]),
    }


# --- Get Model Instance ---
def get_model(tool_name: str, override_model: str | None = None):
    """
    Returns a model instance for the given tool.
    The model used is determined by checking (in order):
    1. The `default_model_override` context variable.
    2. The `DEFAULT_MODEL_NAME` environment variable.
    3. The default model specified in config.json for the LLM_PROVIDER.

    For the OpenAI provider:
      - Checks for OPENAI_API_KEY (and optionally OPENAI_BASE_URL)
      - Builds an options dictionary with the API key and compatibility setting
      - Imports and calls create_openai(opt) to get a callable, then passes the model name.

    For the Gemini provider:
      - Checks for GEMINI_API_KEY
      - Imports and calls create_google_generative_ai with the key, then passes the model name.
    """
    tool_config = get_tool_config(tool_name, override_model)
    provider_config = config_json["providers"][LLM_PROVIDER]

    logger.debug(f"[+] Using {LLM_PROVIDER} provider with model {tool_config['model']}")

    if LLM_PROVIDER in ["openai", "litellm"]:
        if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found")
        if LLM_PROVIDER == "litellm" and not LITELLEM_KEY:
            raise ValueError("LITELLEM_KEY not found")
        # Build options for the OpenAI client
        opt = {
            "apiKey": OPENAI_API_KEY if LLM_PROVIDER == "openai" else LITELLEM_KEY,
            "compatibility": provider_config["clientConfig"]["compatibility"],
        }

        if OPENAI_BASE_URL:
            opt["baseURL"] = OPENAI_BASE_URL

        if LITELLEM_BASE_URL and LLM_PROVIDER == "litellm":
            opt["baseURL"] = LITELLEM_BASE_URL

        # Import and create the OpenAI client.
        # Adjust the module path according to your project structure.
        from libAgents.model import (
            create_openai,
        )  # This function should be implemented in your SDK.

        # create_openai(opt) returns a callable that accepts a model name.
        return create_openai(opt)(tool_config["model"])

    elif LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found")
        from libAgents.model import (
            create_google_generative_ai,
        )  # Adjust import as needed.

        return create_google_generative_ai({"apiKey": GEMINI_API_KEY})(
            tool_config["model"]
        )


# --- Validate Required Environment Variables ---
if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found")
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")
if LLM_PROVIDER == "litellm" and not LITELLEM_KEY:
    raise ValueError("LITELLEM_KEY not found")
if LLM_PROVIDER == "litellm" and not LITELLEM_BASE_URL:
    raise ValueError("LITELLEM_BASE_URL not found")
