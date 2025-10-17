# libAgents

A `Deep Search` based agent building framework for `Atlantis` CRS, which is a large scalable bug-finding
system for [oss-fuzz](https://github.com/google/oss-fuzz) projects. The library is built by [Team Atlanta](https://team-atlanta.github.io).


## Quick Start

```python
# setup LiteLLM envs
# export AIXCC_LITELLM_HOSTNAME=<our-litellm-proxy>
# export LITELLM_KEY=sk-xxxx
# (optional) export DEFAULT_MODEL=gpt-4.1

# sanity-check.py
import asyncio
from libAgents.agents import DeepSearchAgent

agent = DeepSearchAgent()
result = asyncio.run(agent.query("Who is Andrew Chi-Chih Yao?"))

print(result) 

# uv run ./examples/sanity-check.py 
# Andrew Chi-Chih Yao is a distinguished computer scientist, celebrated for his groundbreaking contributions in computational theory and cryptography. He is best known for establishing the Yao's Minimax Principle, a fundamental concept in game theory, and the Yao's Garbling scheme, pivotal in secure multi-party computations. Yao's work has profoundly influenced modern computer science, earning him numerous accolades including the prestigious Turing Award. His innovative approaches continue to drive advancements in both theoretical and applied aspects of computer science, making his contributions indispensable to the field.
```

For plugin usage, check our [examples](./examples/). 
To write new plugins, we offer a [template](./libAgents/plugins/template.py) for you to copy/paste.

## Examples

```bash
$ uv venv
$ source .venv/bin/activate
$ uv pip install -e . # -e for dev
$ uv run examples/ls.py
$ uv run examples/[other_example].py
```

## Prerequisites

To use the plugins, you need to install the following external dependencies. Only install the dependencies for the plugins you intend to use:

- Code Browser Plugin: [Userspcae Code Browser](https://github.com/Team-Atlanta/userspace-code-browser/tree/main)

- RipGrep Plugin: `apt install ripgrep`

- Codex: `npm install -g @openai/codex`

- Claude Code: `npm install -g @anthropic-ai/claude-code`

## Deep Search and Deep Research Agent

### Core Idea: Bridging the Knowledge Gap from Initial Query to Final Response

By equipping LLMs with external tools and plugins, we enable them to generate refined prompts based on knowledge gathered from previous steps. Through a finite series of steps—constrained by token limits—that involve reflection, gap-focused questioning, and evaluation, LLMs can provide more comprehensive and accurate responses to complex queries.

### What is Deep Search?

For a given question or query, the agent generates a series of sub-questions designed to break down the problem into manageable parts. By answering these sub-questions, the agent can progressively fill knowledge gaps and converge towards the most accurate and complete final answer. During this process, the agent utilizes various user-provided plugins, such as:

- AnswerPlugin: Evaluate LLM generated answers; propose improvement ideas
- ReflectPlugin: Analyzing the query and identify knowledge gaps
- FsReaderPlugin: To read and extract information from local files
- RipGrepPlugin: To search information from file system using RipGrep
- SedPlugin: Use together with ripgrep to print the code regions
- CoderPlugin: Write scripts and run in a small sandbox (currently based on Aider)
- CodeBrowserPlugin: To index and analyze the local code base.  
    - You can pass `CODE_BROWSER_ADDRESS` env variable to use a pre-defined daemon

The modularity of plugins allows the agent to adapt to different domains and sources of information.

### What is Deep Research?

Deep Research involves planning and executing complex tasks by breaking them down into multiple structured steps or sections. Examples include:

- Building an end-to-end website
- Writing a comprehensive technical report for a project

For each section of the task, the agent uses Deep Search to retrieve relevant information, organize the findings, and integrate them cohesively to fulfill the overall Deep Research objective. This structured approach ensures thoroughness and accuracy throughout the process.

### How Does the State Machine Work in Our Deep Search Agent (DSA)?

The Deep Search Agent implements a finite state machine that manages the research process through a `ResearchSession` class. This session maintains the core state including step tracking, token budget management, and question state (original question and sub-questions). The agent operates in a plugin-based architecture where each plugin maintains its own state and contributes to a shared knowledge base. The main processing loop iterates until either the question is answered, token budget is exceeded, or no available actions remain. During each iteration, the agent updates its state, generates context-aware prompts, and processes available actions through the plugin system. The agent maintains multiple types of context (action history, knowledge collection, plugin states) and supports context saving for debugging. If normal processing fails, the agent activates a "beast mode" fallback mechanism that uses a simplified prompt with only the answer plugin. This state machine design enables the agent to break down complex queries into manageable steps while maintaining context across iterations and managing resources efficiently.

## How the Plugin System Works

The plugin system is designed to be modular and extensible:

For each step, the `plugin.handle()` function will be triggered according to the `action_type`. 
In the `handle()` function, the plugins need to provide necessary `diary_contexts` and plugin-specific `knowledges`,
which will later be used to generate the prompt for the next round. The plugin can manage its core states, either through
custom class members or general `PluginState`.


## Debugging and Context Dumping

The framework provides several debugging features:

For debugging, we store the iteration context in `ResearchSession.context_store` (by default: it is `$PWD/context_store`).
By checking the interaction histories and generated prompts, the debugging process can be easier.

## LLM Abstraction

`libAgents` replicates [AI-SDK](https://sdk.vercel.ai/docs/reference/ai-sdk-core/generate-object)'s `generateObject` API 
for `json_schema`-based LLM interaction. When replicating `AI-SDK`-based agents, it can be much easier.

### Configuring LLM Models

By default, all configurations are loaded from [config.json](./libAgents/config.json).

To explicitly control the model name, you can override it using either a ContextVar or the environment variable `DEFAULT_MODEL_NAME`.

```python
# Using contextvars
from libAgents.model import model_override
agent = DeepSearchAgent()
with model_override(model_name):
    result = await agent.query("What is the capital of France?")
    assert "Paris" in result

# Using an environment variable (not thread-safe)
from libAgents.utils import environ
with environ("DEFAULT_MODEL_NAME", model_name):
    agent = DeepSearchAgent()
    result = await agent.query("What is the capital of France?")
    assert "Paris" in result
```


### Agents

- **Deep Search Agent** (`./libAgents/agents/deep_search_agent.py`): Automatic, step-by-step deep search agent.
- **Diff Analysis Agent** (`./libAgents/agents/diff_analysis_agent.py`): Analyzes diffs using the Deep Search Agent.
- **Stepwise Agent** (`./libAgents/agents/stepwise_agent.py`): Generates step-by-step plans for long or complex queries.


### Agent FLow

libAgents supports basic agent flow by overloading the `>>` operator. check the example [here](./tests/test_agents/test_agent_flow.py).

## Testing

```bash
pytest -v ./tests
```

During testing, we often need to access the specified oss-fuzz project repository or source directory.
To simplify writing tests, we provide two helper functions: `pytest.get_oss_repo` and `pytest.get_oss_project`.
Please check [test_ripgrep_nginx_src](./tests/test_plugins/test_ripgrep.py) as an example.
