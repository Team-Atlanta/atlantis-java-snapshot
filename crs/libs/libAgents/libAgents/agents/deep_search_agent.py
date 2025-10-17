import json
import logging
import os
import traceback
import asyncio
import diskcache
from pathlib import Path
from typing import Any, Dict, List, Optional

from libAgents.base import ActionPlugin, ActionRegistry
from libAgents.config import get_model
from libAgents.error import handle_generate_object_error
from libAgents.model import generate_object
from libAgents.utils import Project
from libAgents.plugins import (
    AnswerPlugin,
    ReflectPlugin,
    CodeBrowserPlugin,
    CoderPlugin,
    ListDirPlugin,
    RipGrepPlugin,
    SedPlugin,
    AskCodebasePlugin,
)
from libAgents.session import ResearchSession

# disable the annoying httpx INFO logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class AgentBase:
    def __init__(self, name: Optional[str] = None, **kwargs):
        self.name = name or self.__class__.__name__
        self.next_agent: Optional["AgentBase"] = None
        self.data = kwargs

    def __rshift__(self, other):
        self.next_agent = other
        return other

    async def start(self, input_data=None):
        output = await self.run(input_data)
        if self.next_agent is not None:
            return await self.next_agent.start(output)
        return output

    async def run(self, input_data):
        raise NotImplementedError("Subclasses must implement this method")


class AgentFlow:
    def __init__(self, start_agent: AgentBase):
        self.start_agent = start_agent

    async def run(self, input_data=None):
        return await self.start.start(input_data)


class DeepSearchAgent(AgentBase):
    """
    Deep Search Agent (DSA) that uses a plugin-based architecture for handling different actions.
    """

    def __init__(
        self,
        plugins: Optional[List[ActionPlugin]] = None,
        context_saving_dir: Optional[Path] = None,
        enable_context_saving=False,
        cache_type: Optional[str] = None,
        identifier: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__()
        self.registry = ActionRegistry()
        self.context_saving_dir = context_saving_dir
        self.cache_expire_time = cache_expire_time
        self.identifier = identifier
        self.enable_context_saving = enable_context_saving or int(
            os.environ.get("DEBUG", "0")
        )

        self._load_plugins(plugins)  # don't forget to load plugins
        self._init_cache(cache_type, identifier)

    def _init_code_db(self):
        self.code_db = None

    def _init_cache(self, cache_type: Optional[str], identifier: Optional[str]) -> bool:
        if cache_type is None:
            self.cache = None
            return False
        elif cache_type == "disk":
            if identifier is None:
                raise ValueError("identifier is required when cache_type is disk")
            self.cache = diskcache.Cache(
                f"/tmp/{self.identifier}", size_limit=10 * 1024 * 1024
            )
            logger.info(f"Initialized disk cache for {self.identifier}")
            return True
        elif cache_type == "memory":
            raise NotImplementedError("Memory cache is not implemented yet")
        return False

    def _get_key(self, model_name: str, question: str) -> str:
        return f"{model_name}:{question}"

    def _save_cache(self, key: str, value: Any, expire: Optional[int] = None):
        if self.cache is None:
            return
        self.cache.set(key, value, expire=expire)

    def _get_cache(self, key: str) -> Optional[Any]:
        if self.cache is None:
            return None
        return self.cache.get(key)

    def _load_plugins(self, plugins: List[ActionPlugin]):
        """Load all available action plugins."""
        if plugins is None:
            # default plugins
            plugins = [
                AnswerPlugin(),
                ReflectPlugin(),
            ]

        for plugin in plugins:
            self.registry.register(plugin)
            logger.info(f"Registered plugin: {plugin.action_name}")

    async def query(
        self,
        question: str,
        override_model: Optional[str] = None,
        token_budget: int = 1000_000,
        timeout: int = 300,
        enable_strict: bool = False,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # check cache first
        cached_result = self._get_cache(self._get_key(override_model, question))
        if cached_result is not None:
            return cached_result

        if not self.registry.get_plugins():
            error_msg = "No plugins registered. Please ensure plugins are loaded before querying."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.registry.reset_all_plugin_states()

        session = ResearchSession(
            question=question,
            token_budget=token_budget,
            plugin_registry=self.registry,
            context_saving_dir=self.context_saving_dir,
            override_model=override_model,
        )
        try:
            await session.setup_eval_metrics(enable_strict=enable_strict)
            result = await asyncio.wait_for(
                self._query(session, override_model, messages),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Query timed out. Try Beast mode...")
            is_ok, answer = await self._handle_beast_mode(session, override_model)
            return answer if is_ok else None

        res = result["result"]["answer"]
        # save cache
        self._save_cache(
            self._get_key(override_model, question), res, expire=self.cache_expire_time
        )
        return res

    async def _query(
        self,
        session: ResearchSession,
        override_model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # remove the system message if provided
        if messages is not None:
            messages = [msg for msg in messages if msg.get("role") != "system"]
        session.original_messages = messages

        # Main processing loop
        while session.should_continue():
            # Update step and check budget
            session.next_step()  # step += 1, totalStep +=1
            budget_percentage = session.get_budget_percentage()
            current_question = session.get_current_question()
            logger.info(
                f'🤡 Step {session.total_step} / Budget used {budget_percentage}% _QA_ ({session.step % len(session.gaps)}/{len(session.gaps)}): ❓ "{current_question}"'
            )
            # Generate prompt with available actions
            prompt = session.get_prompt()

            try:
                # Get available plugins for schema generation
                available_plugins = session.get_available_plugins()
                messages_with_knowledge = session.compose_messages(
                    current_question, session.original_messages
                )
                session.current_messages = messages_with_knowledge
                # logger.debug(f"Messages: {messages}")
                result = await generate_object(
                    model=get_model("agent", override_model),
                    schema=self.registry.get_schema_from_plugins(
                        session, available_plugins
                    ),
                    system=prompt,
                    messages=messages_with_knowledge,
                    temperature=1,
                )

                try:
                    if result.object is None:
                        logger.error("Received None object from generate_object")
                        obj = {
                            "action": "answer",
                            "thoughts": "Failed to generate response",
                            "action-details": {
                                "answer": "Failed to process query due to a system error."
                            },
                        }
                    else:
                        obj = json.loads(result.object)
                except Exception as e:
                    logger.error(f"Error parsing JSON: {e}\n{traceback.format_exc()}")
                    logger.error(f"Raw object: {result.object}")
                    results = await handle_generate_object_error(e)
                    obj = (
                        json.loads(results.object)
                        if results.object is not None
                        else {
                            "action": "answer",
                            "thoughts": "Error recovery failed",
                            "action-details": {
                                "answer": "Failed to process query due to a system error."
                            },
                        }
                    )
                session.token_tracker.track_usage("agent", result.usage.total_tokens)
                session.this_step = obj
                logger.debug(
                    f">>>> [{session.this_step.get('action')}] ⬅️  ({', '.join([p.action_name for p in available_plugins])})"
                )
                logger.debug(f">> 🧐 Thoughts: {obj.get('thoughts')}")
                # logger.debug(f">> 🔄 gaps: {session.gaps}")
                logger.debug(f"\n{json.dumps(obj.get('action-details'), indent=2)}\n")

                # Handle the action through plugin system
                action = obj.get("action")
                if action:
                    plugin = self.registry.get_plugin(action)
                    if plugin and plugin.is_available(session):
                        await plugin._handle(session, current_question)
                    else:
                        logger.error(
                            f"Action {action} not available or plugin not found"
                        )

                # Store context for debugging
                if self.enable_context_saving:
                    await session.save_context(prompt, session.total_step)

                if session.is_answered or session.force_beast_mode:
                    break

            except Exception as e:
                logger.debug(f"Error in DSA main query loop: {e}")
                logger.debug(traceback.format_exc())
                try:
                    results = await handle_generate_object_error(e)
                    obj = (
                        json.loads(results.object)
                        if results.object is not None
                        else {
                            "action": "answer",
                            "thoughts": "Error recovery failed",
                            "action-details": {
                                "answer": "An error occurred during query processing."
                            },
                        }
                    )
                except Exception as nested_e:
                    logger.error(f"Error in error handling: {nested_e}")
                    obj = {
                        "action": "answer",
                        "thoughts": "Error in error handling",
                        "action-details": {
                            "answer": "An error occurred during query processing."
                        },
                    }
                session.this_step = obj
                if self.enable_context_saving:
                    await session.save_context(prompt, session.total_step)
                break
        # end of main processing loop

        # Handle beast mode if needed
        if not session.is_answered or session.force_beast_mode:
            await self._handle_beast_mode(session, override_model)

        return {
            "result": session.this_step["action-details"],
            "context": session.get_context(),
        }

    async def _handle_beast_mode(
        self, session: ResearchSession, override_model: Optional[str] = None
    ):
        """Handle beast mode when normal processing fails."""
        logger.info("Enter Beast mode!!!")
        session.next_step()

        prompt = session.get_beast_mode_prompt()
        model_beast = get_model("agentBeastMode", override_model)

        try:
            # Get only the answer plugin for beast mode
            answer_plugin = next(
                (
                    plugin
                    for plugin in self.registry.get_plugins()
                    if plugin.action_name == "answer"
                ),
                None,
            )

            if not answer_plugin:
                logger.error(
                    "Answer plugin not found for beast mode, and it is required for json schema"
                )
                return

            message_with_knowledge = session.compose_messages(
                session.get_current_question(), session.original_messages
            )
            result = await generate_object(
                model=model_beast,
                schema=self.registry.get_schema_from_plugins(
                    session, [answer_plugin]
                ),  # beast mode is a special answer_plugin
                system=prompt,
                messages=message_with_knowledge,
                temperature=1,
            )
            logger.debug(
                f"LLM call in beast mode completed. Result object: {result.object[:200] if result and result.object else 'N/A'}"
            )
            obj = json.loads(result.object)
            session.token_tracker.track_usage("agent", result.usage.total_tokens)
            session.this_step = obj
            logger.info(session.this_step)

            if self.enable_context_saving:
                await session.save_context(prompt, session.total_step)
            return True, obj["action-details"]["answer"]

        except Exception as e:
            logger.error(f"Error in beast mode: {e}")
            logger.error(traceback.format_exc())
            obj = {
                "action": "answer",
                "thoughts": "Error in error handling",
                "action-details": {"answer": None},
            }
            session.this_step = obj
            return False, obj["action-details"]["answer"]


class DeepThinkAgent(AgentBase):
    """
    An agent with full plugins support and agent flow support.
    """

    def __init__(
        self,
        model: str,
        project_bundle: Project,
        timeout: int = 300,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 300,
        enable_aider: bool = True,
        enable_codebrowser: bool = True,
    ):
        plugins = [
            AnswerPlugin(),
            ReflectPlugin(),
            RipGrepPlugin(),
            SedPlugin(),
            ListDirPlugin(),
        ]

        # if "claude" not in model and "gemini" not in model:
        #     plugins.append(AskCodebasePlugin(
        #         project_name=project_bundle.name,
        #         src_path=project_bundle.repo_path,
        #     ))

        if enable_aider:
            plugins.append(CoderPlugin(
                project_name=project_bundle.name,
                main_repo=project_bundle.repo_path,
            ))

        # Add CodeBrowserPlugin only for C/C++ projects
        if enable_codebrowser and (project_bundle.language == "c++" or project_bundle.language == "c"):
            plugins.append(
                CodeBrowserPlugin(
                    project_name=project_bundle.name,
                    src_path=project_bundle.repo_path,
                )
            )
        self.deep_search_agent = DeepSearchAgent(
            plugins=plugins,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
            identifier=project_bundle.name,
        )
        self.model = model
        self.timeout = timeout

    async def run(self, input_data):
        return await self.deep_search_agent.query(
            input_data, self.model, timeout=self.timeout
        )


class HybridAgent(AgentBase):
    pass