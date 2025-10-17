import asyncio
import json
import logging
import traceback
from typing import Any, Dict, List, override

from pydantic import Field

from libAgents.base import (
    ENABLE_IN_NEXT_ROUND,
    ActionPlugin,
    BaseKnowledge,
)
from libAgents.session import ResearchSession
from libAgents.tools import CodeBrowser

logger = logging.getLogger(__name__)


class XrefKnowledge(BaseKnowledge):
    """Knowledge about cross references"""

    callee: str = Field(description="Name of the function being called")
    callers: List[str] = Field(
        default_factory=list, description="List of caller function names"
    )

    def knowledge_question(self) -> str:
        return f"What functions call {self.callee}?"

    def knowledge_answer(self) -> str:
        return f"""
<caller-functions>
{chr(10).join(f"- {caller}" for caller in self.callers)}
</caller-functions>
"""


class TypeKnowledge(BaseKnowledge):
    """Knowledge about type definitions"""

    name: str = Field(description="Name of the type")
    definition: str = Field(description="The actual type definition")
    filename: str = Field(description="Source file path")
    def_type: str = Field(description="Type of definition (FUNCTION, TYPEDEF, etc.)")

    def knowledge_question(self) -> str:
        return f"What is the type definition of {self.name}?"

    def knowledge_answer(self) -> str:
        return f"""
<filename>
{self.filename}
</filename>

<type-definition>
{self.definition}
</type-definition>
"""


class FunctionKnowledge(BaseKnowledge):
    """Knowledge about function definitions"""

    name: str = Field(description="Name of the function")
    definition: str = Field(description="The actual function definition")
    filename: str = Field(description="Source file path")
    def_type: str = Field(description="Type of definition (FUNCTION, TYPEDEF, etc.)")
    references: List[str] = Field(
        default_factory=list, description="List of referenced symbols"
    )

    def knowledge_question(self) -> str:
        return f"What is the function definition of {self.name}?"

    def knowledge_answer(self) -> str:
        return f"""
<filename>
{self.filename}
</filename>

<function-definition>
{self.definition}
</function-definition>

<called-functions>
{chr(10).join(f"- {ref}" for ref in self.references)}
</called-functions>
"""


class CodeBrowserPlugin(ActionPlugin):
    """
    A plugin wrapper for userspace-browser
    > https://github.com/Team-Atlanta/userspace-code-browser
    """

    def __init__(self, project_name: str, src_path: str, max_targets: int = 50):
        self.project_name = project_name
        self.src_path = src_path
        self.max_targets = max_targets

        # Track seen targets separately for each action type
        self.seen_type_targets = set()
        self.seen_function_targets = set()
        self.seen_xref_targets = set()

        # Use the singleton CodeBrowser instance for this src_path
        # Port can be None to let the CodeBrowser find an available port
        code_browser = CodeBrowser(project_name, src_path)
        self.db_client = code_browser.db_client
        # Store the actual port that was used (either provided or auto-discovered)
        self.port = code_browser.server_port

        self.handlers = {
            "type_query": self.read_data_structures_async,
            "function_query": self.read_functions_async,
            "cross_reference": self.read_cross_references_async,
        }

    @property
    @override
    def action_name(self) -> str:
        return f"code-browser-({self.project_name})"

    @override
    def get_schema_properties(self, session: ResearchSession) -> Dict[str, Any]:
        return {
            "action_type": {
                "type": "string",
                "enum": ["type_query", "function_query", "cross_reference"],
                "description": "The action type for the targets you provide",
            },
            "targets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The targets you want to perform the action on, must be an array of unique function names, maxItems is 2",
                "maxItems": 2,
            },
        }

    @override
    def get_prompt_section(self, session: ResearchSession) -> str:
        """Get the code browsing action prompt section."""
        return f"""<action-{self.action_name}>
- Browser the type definition, function definition, and cross references of the targets you provided.
- As it only works ofr C-based projects, if this action cannot find any relevant code snippets, try <action-ripgrep> and <action-sed>.
</action-{self.action_name}>"""

    @override
    def is_available(self, session: ResearchSession) -> bool:
        """Check if code search action is available.
        This function will be called at the beginning of each round.
        """
        try:
            total_seen = (
                len(self.seen_type_targets)
                + len(self.seen_function_targets)
                + len(self.seen_xref_targets)
            )
            return total_seen < self.max_targets
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False

    def get_seen_targets_for_action(self, action_type: str) -> set:
        """Get the appropriate seen targets set for the given action type."""
        if action_type == "type_query":
            return self.seen_type_targets
        elif action_type == "function_query":
            return self.seen_function_targets
        elif action_type == "cross_reference":
            return self.seen_xref_targets
        else:
            return set()

    def read_data_structure(self, target: str) -> str:
        result = self.db_client.get_any_type_definition(target)
        return result

    def read_function(self, target: str) -> str:
        result = self.db_client.get_function_definition(target)
        return result

    def xref_function(self, target: str) -> str:
        result = self.db_client.get_function_cross_references(target)
        return result

    async def read_elements_async(
        self, targets: List[str], action_func
    ) -> List[Dict[str, Any]]:
        results = []
        tasks = []

        for target in targets:
            try:
                task = asyncio.to_thread(action_func, target)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task for target {target}: {e}")
                continue

        try:
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            for target, result in zip(targets, raw_results):
                if isinstance(result, Exception):
                    logger.error(f"Error reading target {target}: {result}")
                    continue
                if result:
                    try:
                        if isinstance(result, str):
                            parsed = json.loads(result)
                            results.extend(
                                parsed if isinstance(parsed, list) else [parsed]
                            )
                        else:
                            results.extend(
                                result if isinstance(result, list) else [result]
                            )
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse result for {target}")
                        continue

        except Exception as e:
            logger.error(f"Error gathering results: {e}")

        return results

    # Convenience async methods for different types of code elements
    async def read_functions_async(self, targets: List[str]) -> List[Dict[str, Any]]:
        """Asynchronously read multiple functions."""
        return await self.read_elements_async(targets, self.read_function)

    async def read_data_structures_async(
        self, targets: List[str]
    ) -> List[Dict[str, Any]]:
        """Asynchronously read multiple data structures."""
        return await self.read_elements_async(targets, self.read_data_structure)

    async def read_cross_references_async(
        self, targets: List[str]
    ) -> List[Dict[str, Any]]:
        """Asynchronously read cross references for multiple targets."""
        return await self.read_elements_async(targets, self.xref_function)

    def add_type_knowledge(
        self, session: ResearchSession, result: Dict[str, Any]
    ) -> None:
        """Add type knowledge to the session."""
        knowledge = TypeKnowledge(
            source=self.action_name,
            knowledge_type="type_definition",
            name=result["name"],
            definition=result["definition"],
            filename=result["filename"],
            def_type=result["def_type"],
        )
        session.add_knowledge(knowledge)

    def add_function_knowledge(
        self, session: ResearchSession, result: Dict[str, Any]
    ) -> None:
        """Add function knowledge to the session."""
        knowledge = FunctionKnowledge(
            source=self.action_name,
            knowledge_type="function_definition",
            name=result["name"],
            definition=result["definition"],
            filename=result["filename"],
            def_type=result["def_type"],
            references=result.get("references", []),
        )
        session.add_knowledge(knowledge)

    def add_xref_knowledge(
        self, session: ResearchSession, callee: str, callers: List[str]
    ) -> None:
        """Add cross-reference knowledge to the session."""
        knowledge = XrefKnowledge(
            source=self.action_name,
            knowledge_type="cross_reference",
            callee=callee,
            callers=callers,
        )
        session.add_knowledge(knowledge)

    @override
    async def handle(self, session: ResearchSession, current_question: str) -> bool:
        """Handle code search action."""
        action_type = session.get_action_param("action_type")
        targets = session.get_action_param("targets")

        if not targets:
            logger.debug(f"❗[{self.action_name}] No code search targets")
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But you did not specify any code search targets.
"""
            )
            return ENABLE_IN_NEXT_ROUND

        try:
            # Get the appropriate seen targets set for this action type
            seen_targets = self.get_seen_targets_for_action(action_type)

            # Filter out targets we already have processed for this action type
            unique_targets = [t for t in targets if t not in seen_targets]

            if not unique_targets:
                session.add_diary_entry(
                    f"""At step {session.step}, you took **{self.action_name}** action.
Attempted to do {action_type} on: "{", ".join(targets)}"
But you realized you have already searched these targets before for this action type.
"""
                )
                return ENABLE_IN_NEXT_ROUND

            # Get search results using appropriate handler
            search_results = await self.handlers[action_type](unique_targets)

            if not search_results:
                logger.debug(f"❗[{self.action_name}] No search results")
                session.add_diary_entry(
                    f"""At step {session.step}, you took **{self.action_name}** action.
You did the action: "{action_type}" on: "{", ".join(unique_targets)}".
But cannot find any relevant code snippets, which means you shouldn't search the same targets again.
"""
                )
                # Mark targets as seen even if no results to avoid retrying
                seen_targets.update(unique_targets)
                return ENABLE_IN_NEXT_ROUND

            # Process and store new knowledge based on action type
            logger.debug(
                f"[{self.action_name}] Processing {len(search_results)} results"
            )
            processed_targets = []

            if action_type == "cross_reference":
                # For cross references, create a mapping of callee -> [callers]
                for target in unique_targets:
                    # Find all functions that call this target
                    callers = [
                        result["name"]
                        for result in search_results
                        if target in result.get("references", [])
                    ]
                    if callers:
                        self.add_xref_knowledge(session, target, callers)
                        processed_targets.append(target)
                        seen_targets.add(target)
            else:
                # For type and function queries, process each result
                for result in search_results:
                    try:
                        if action_type == "type_query":
                            self.add_type_knowledge(session, result)
                        elif action_type == "function_query":
                            self.add_function_knowledge(session, result)

                        processed_targets.append(result["name"])
                        seen_targets.add(result["name"])
                    except Exception as e:
                        logger.error(
                            f"Error processing result for {result.get('name', 'unknown')}: {e}"
                        )
                        logger.error(f"Stack trace: {traceback.format_exc()}")
                        continue

            if not processed_targets:
                session.add_diary_entry(
                    f"""At step {session.step}, you took **{self.action_name}** action.
You did the action: "{action_type}" on: "{", ".join(unique_targets)}".
But failed to process any of the results.
"""
                )
                return ENABLE_IN_NEXT_ROUND

            # Success case
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
You did the action: "{action_type}" on: "{", ".join(unique_targets)}".
Found and stored new knowledge for: {", ".join(processed_targets)}
"""
            )

        except Exception as e:
            logger.error(f"[{self.action_name}] Error: {e}")
            session.add_diary_entry(
                f"""At step {session.step}, you took **{self.action_name}** action.
But encountered an error: {e!s}
"""
            )
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise e

        return ENABLE_IN_NEXT_ROUND
