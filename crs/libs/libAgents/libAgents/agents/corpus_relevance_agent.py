import logging
from libAgents.agents import AgentBase, DeepThinkAgent
from libAgents.utils import Project
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import json
from libAgents.model import generate_text
from libAgents.config import get_model

logger = logging.getLogger(__name__)
'''
   - Use the code-browser plugin to analyze the harness code at the provided path
'''

HARNESS_FORMAT_ANALYSIS_PROMPT = '''
You are an expert in program analysis and fuzzing, tasked with analyzing fuzzing harnesses to determine their input format requirements and project categories.

Your goal is to analyze ALL fuzzing harnesses in the target repository and determine:
1. The input format requirements
2. The project category/domain
3. Any specific format validation or constraints

## Project Information
- Project Name: {project_name}
- Source Repository Path: {source_code_repository_path}

## Harness Information
{harness_info}

## Category Guidance
Both project_category and harness project_category should be specific protocols, data formats, languages, etc. Examples:

- HTML: Web markup language for structuring web pages
- WebAssembly (WASM): Binary instruction format for web browsers
- Zstandard (ZST): Data compression format
- FLAC: Free Lossless Audio Codec format
- JavaScript (JS): Programming language for web browsers
- TLS/SSL: Security protocols

## Required Analysis Steps
You MUST follow these steps in order:

1. For EACH harness listed above (you MUST analyze ALL harnesses):
   - If the path is not a file, use list_dir to locate the correct path
   - Use the ripgrep plugin to find related implementations
   - Use the sed plugin to read specific lines of the harness code
   - Pay special attention to:
     * Input format requirements
     * Data structures used
     * Protocol specifications
     * Format validation logic
     * Error handling patterns

2. Based on the harness analysis:
   - Identify the input formats and protocols used
   - Note any specific format requirements
   - Determine the project category/domain (use specific format/protocol names from examples)
   - Look for existing test cases or examples in the project

3. Determine the overall project category:
   - Do NOT get distracted by the harnesses, focus on the project as a whole
   - You may use your domain knowledge to determine the overall project category
   - You may also crawl the repository for documentation or other information to help you determine the overall project category
   - Consider the project's main purpose and functionality
   - Select the most specific format/protocol that best describes the project
   - If the project handles multiple formats, choose the primary one

## Required Output Format
You MUST provide your response as a single line of valid JSON with no newlines, no extra whitespace, no surrounding backticks, no other text. The JSON must follow this exact structure:

{{"analysis":"Your detailed analysis here","project_category":"specific format/protocol from examples","harness_mappings":{{"harness_name":{{"input_formats":["format1","format2"],"project_category":"specific format/protocol from examples","format_requirements":["requirement1","requirement2"],"analysis_details":"Detailed explanation of the analysis"}}}},"additional_notes":"Any additional important considerations"}}

IMPORTANT:
1. The response MUST be a single line of valid JSON with no newlines or extra whitespace
2. You MUST include an entry for EVERY harness in the harness_mappings object
3. For each harness, include format_requirements and analysis_details
4. Do not add any formatting, indentation, or line breaks to the JSON
5. You MUST use the available tools to inspect the harnesses before making any recommendations
6. If you cannot determine the format for a harness, include it in the output with empty arrays and "Unknown" category
7. Use specific format/protocol names from the examples above for both project_category and harness project_category
8. Be careful around escape characters, better to avoid altogether
'''

CORPUS_MATCHING_PROMPT = '''
You are an expert in program analysis and fuzzing, tasked with matching project categories and input formats with relevant corpus categories.

Your goal is to analyze the format analysis results and determine which corpus categories could be useful for testing based on input format compatibility and project category.

## Project Information
- Project Name: {project_name}
- Available Corpus Categories: {available_categories}

## Format Analysis Results
{format_analysis}

## IMPORTANT: Category Selection Guidelines
- Select ONLY the MOST RELEVANT category for each harness
- Each harness should ideally match to a SINGLE category
- For the overall project, select at most 2-3 categories maximum
- Prioritize exact format matches over similar domains
- If no exact match exists, choose the closest format/protocol match
- Avoid selecting multiple categories unless absolutely necessary

## Required Analysis Steps
You MUST follow these steps in order:

1. For the overall project category:
   - Do NOT get distracted by the harnesses, focus on the project as a whole
   - Review the project_category from the format analysis
   - Look for corpus categories that handle the same format/protocol
   - Consider categories that implement similar functionality
   - Note any format conversion requirements
   - Select at most 2-3 most relevant categories from the available_categories list

2. For each harness in the format analysis:
   - Do NOT get distracted by project_category, focus on this harness's input formats
   - Review the input formats and project category
   - Consider format compatibility requirements
   - Evaluate potential format conversion needs
   - Look for categories with similar domains
   - Select ONLY the SINGLE most relevant category for this harness

3. Match with available corpus categories:
   - Consider categories that share similar input formats and protocols
   - Look for categories that handle similar data structures
   - Evaluate categories based on their domain and functionality
   - Note any format conversion requirements
   - Prioritize exact format matches

## Required Output Format
You MUST provide your response as a single line of valid JSON with no newlines, no extra whitespace, no surrounding backticks, no other text. The JSON must follow this exact structure:

{{"analysis":"Your detailed analysis here","project_matches":{{"compatible_categories":["category1","category2"],"format_requirements":["requirement1","requirement2"],"compatibility_reasoning":"Explanation of why these categories are compatible"}},"harness_mappings":{{"harness_name":{{"compatible_categories":["category1"],"format_requirements":["requirement1","requirement2"],"compatibility_reasoning":"Explanation of why this category is compatible"}}}},"additional_notes":"Any additional important considerations"}}

IMPORTANT:
1. The response MUST be a single line of valid JSON with no newlines or extra whitespace
2. List only categories that exist in the available_categories list
3. Include format_requirements and compatibility_reasoning for both project and harness matches
4. Do not add any formatting, indentation, or line breaks to the JSON
5. Be careful around escape characters, better to avoid altogether
6. Each harness should have at most 1-2 categories in compatible_categories
7. Project should have at most 2-3 categories in compatible_categories
'''

BACKUP_HARNESS_FORMAT_ANALYSIS_PROMPT = '''
You are an expert in program analysis and fuzzing, tasked with analyzing an open source project's categories for data formats, protocols, languages, etc.

## Project Information
- Project Name: {project_name}

## Category Guidance
Project category should be specific protocols, data formats, languages, etc. Examples:

- HTML: Web markup language for structuring web pages
- WebAssembly (WASM): Binary instruction format for web browsers
- Zstandard (ZST): Data compression format
- FLAC: Free Lossless Audio Codec format
- JavaScript (JS): Programming language for web browsers
- TLS/SSL: Security protocols

## Analysis
Determine the overall project category:
- You may use your domain knowledge to determine the overall project category
- Consider the project's main purpose and functionality
- Select the most specific format/protocol that best describes the project
- If the project handles multiple formats, choose the primary one

## Required Output Format
You MUST provide your response as a single line of valid JSON with no newlines, no extra whitespace, no surrounding backticks, no other text. The JSON must follow this exact structure:

{{"analysis":"Your detailed analysis here","project_category":"specific format/protocol from examples","additional_notes":"Any additional important considerations"}}

IMPORTANT:
1. The response MUST be a single line of valid JSON with no newlines or extra whitespace
2. Do not add any formatting, indentation, or line breaks to the JSON
3. Be careful around escape characters, better to avoid altogether
4. Use specific format/protocol names from the examples above for project_category
'''

BACKUP_CORPUS_MATCHING_PROMPT = '''
You are an expert in program analysis and fuzzing, tasked with matching project categories and input formats with relevant corpus categories.

Your goal is to analyze the format analysis results and determine which corpus categories could be useful for testing based on input format compatibility and project category.

## Project Information
- Project Name: {project_name}
- Available Corpus Categories: {available_categories}

## Format Analysis Results
{format_analysis}

## IMPORTANT: Category Selection Guidelines
- Select ONLY the MOST RELEVANT category for each harness
- Each harness should ideally match to a SINGLE category
- For the overall project, select at most 2-3 categories maximum
- Prioritize exact format matches over similar domains
- If no exact match exists, choose the closest format/protocol match
- Avoid selecting multiple categories unless absolutely necessary

## Required Analysis Steps
You MUST follow these steps in order:

1. For the overall project category:
   - Do NOT get distracted by the harnesses, focus on the project as a whole
   - Review the project_category from the format analysis
   - Look for corpus categories that handle the same format/protocol
   - Consider categories that implement similar functionality
   - Note any format conversion requirements
   - Select at most 2-3 most relevant categories from the available_categories list

2. Match with available corpus categories:
   - Consider categories that share similar input formats and protocols
   - Look for categories that handle similar data structures
   - Evaluate categories based on their domain and functionality
   - Note any format conversion requirements
   - Prioritize exact format matches

## Required Output Format
You MUST provide your response as a single line of valid JSON with no newlines, no extra whitespace, no surrounding backticks, no other text. The JSON must follow this exact structure:

{{"analysis":"Your detailed analysis here","project_matches":{{"compatible_categories":["category1","category2"],"format_requirements":["requirement1","requirement2"],"compatibility_reasoning":"Explanation of why these categories are compatible"}},"additional_notes":"Any additional important considerations"}}

IMPORTANT:
1. The response MUST be a single line of valid JSON with no newlines or extra whitespace
2. List only categories that exist in the available_categories list
3. Do not add any formatting, indentation, or line breaks to the JSON
4. Be careful around escape characters, better to avoid altogether
5. Project should have at most 2-3 categories in compatible_categories
'''

class HarnessFormatAnalyzerAgent(AgentBase):
    """
    Agent that analyzes a repository's fuzzing harnesses to determine their input format
    requirements and project categories.
    """

    def __init__(
        self,
        model: str,
        project_bundle: Project,
        timeout: int = 600,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__()
        self.model = model
        self.project_bundle = project_bundle
        self.deep_think_agent = DeepThinkAgent(
            model,
            project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
        )

    def _get_harness_info(self) -> str:
        """Generate detailed information about each harness in the project."""
        harness_info = []
        for harness_name, harness_data in self.project_bundle.harnesses.items():
            harness_path = harness_data.get("path", "[Not Available]")
            harness_info.append(f"{harness_name}: {harness_path}")
        return "\n".join(harness_info)

    def __prompt(self) -> str:
        """Generate the prompt for the DeepThinkAgent."""
        return HARNESS_FORMAT_ANALYSIS_PROMPT.format(
            project_name=self.project_bundle.name,
            source_code_repository_path=self.project_bundle.repo_path,
            harness_info=self._get_harness_info()
        )

    async def run(self, _input=None) -> Dict:
        """Run the harness format analysis."""
        prompt = self.__prompt()
        return await run_with_json_parsing_generic(prompt, lambda p: self.deep_think_agent.run(p))

    async def run_backup(self, _input=None) -> Dict:
        """Backup: Run the harness format analysis using generate_text instead of DeepThinkAgent."""
        prompt = self.__prompt()
        model_client = get_model("corpus_relevance", self.model)
        return await harness_format_analysis_backup(model_client, prompt)

class CorpusMatcherAgent(AgentBase):
    """
    Agent that matches format analysis results with relevant corpus categories.
    """

    def __init__(
        self,
        model: str,
        project_bundle: Project,
        available_categories: List[str],
        timeout: int = 600,
        cache_type: Optional[str] = None,
        cache_expire_time: int = 1800,
    ):
        super().__init__()
        self.model = model
        self.project_bundle = project_bundle
        self.available_categories = available_categories
        self.deep_think_agent = DeepThinkAgent(
            model,
            project_bundle,
            timeout=timeout,
            cache_type=cache_type,
            cache_expire_time=cache_expire_time,
        )

    def __prompt(self, format_analysis: Dict) -> str:
        """Generate the prompt for the DeepThinkAgent."""
        return CORPUS_MATCHING_PROMPT.format(
            project_name=self.project_bundle.name,
            available_categories=self.available_categories,
            format_analysis=json.dumps(format_analysis)
        )

    async def run(self, format_analysis: Dict) -> Dict[str, List[str]]:
        """Run the corpus matching analysis."""
        prompt = self.__prompt(format_analysis)
        answer_data = await run_with_json_parsing_generic(prompt, lambda p: self.deep_think_agent.run(p))
        return process_corpus_matches(answer_data, self.available_categories)

    async def run_backup(self, format_analysis: Dict) -> Dict[str, List[str]]:
        """Backup: Run the corpus matching analysis using generate_text instead of DeepThinkAgent."""
        prompt = self.__prompt(format_analysis)
        model_client = get_model("corpus_relevance", self.model)
        return await corpus_matcher_backup(model_client, prompt, self.available_categories)

def parse_json_response(response: str) -> Dict:
    """Clean and parse a JSON response string, with logging and error handling."""
    try:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        cleaned_response = " ".join(response.split())
        answer_data = json.loads(cleaned_response)
        logger.info(f"Parsed JSON response: {answer_data}")
        return answer_data
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON answer: {e}")
        logger.error(f"Response text: {response}")
        return {}

async def run_with_json_parsing_generic(prompt: str, llm_call) -> Dict:
    """Run the given LLM call (async function) and parse the JSON response."""
    try:
        response = await llm_call(prompt)
        logger.debug(f"Full response from LLM call:\n{response}")
        return parse_json_response(response)
    except Exception as e:
        logger.error(f"Error during agent execution: {e}")
        return {}

def process_corpus_matches(answer_data: Dict, available_categories: list) -> Dict[str, list]:
    """Extract and combine project/harness matches from answer_data."""
    project_matches = answer_data.get("project_matches", {})
    project_compatible_categories = project_matches.get("compatible_categories", [])
    project_matches = [
        category for category in project_compatible_categories 
        if category in available_categories
    ]
    # Limit project matches to at most 3 categories
    project_matches = project_matches[:3]
    
    result = {}
    harness_mappings = answer_data.get("harness_mappings", {})
    if len(harness_mappings) == 0:
        # If no harness mappings, add project-level matches under project_name
        result["project"] = sorted(project_matches)
    else:
        # Process harness mappings as before
        for harness_name, mapping in harness_mappings.items():
            harness_compatible_categories = mapping.get("compatible_categories", [])
            harness_matches = [
                category for category in harness_compatible_categories 
                if category in available_categories
            ]
            # Limit harness matches to at most 2 categories, prioritizing the first matches
            harness_matches = harness_matches[:2]
            all_matches = list(set(project_matches + harness_matches))
            # Limit total matches to at most 2 categories per harness
            result[harness_name] = sorted(all_matches)[:2]
    logger.info(f"Parsed structured answer: {result}")
    return result

async def harness_format_analysis_backup(model_client, prompt: str) -> Dict:
    """Standalone backup for harness format analysis using generate_text."""
    async def llm_call(p):
        response_wrapper = await generate_text(model_client, p)
        return response_wrapper.object
    return await run_with_json_parsing_generic(prompt, llm_call)

async def corpus_matcher_backup(model_client, prompt: str, available_categories: list) -> Dict[str, list]:
    """Standalone backup for corpus matcher using generate_text."""
    async def llm_call(p):
        response_wrapper = await generate_text(model_client, p)
        return response_wrapper.object
    answer_data = await run_with_json_parsing_generic(prompt, llm_call)
    return process_corpus_matches(answer_data, available_categories)

async def analyze_corpus_relevance(
    model: str,
    project_bundle: Project,
    available_categories: List[str],
    timeout: int = 600,
    cache_type: Optional[str] = None,
    cache_expire_time: int = 1800,
    use_backup_format_analyzer: bool = False,
    use_backup_corpus_matcher: bool = False,
) -> Tuple[Dict, Dict[str, List[str]]]:
    """
    Analyze which corpus categories could be useful for testing a given repository.
    This function combines both format analysis and corpus matching steps.

    Args:
        model: The model to use for analysis
        project_bundle: The project bundle containing repository and harness information
        available_categories: List of available corpus categories to match against
        timeout: Timeout for the analysis in seconds
        cache_type: Type of cache to use (e.g., "disk")
        cache_expire_time: Cache expiration time in seconds
        use_backup_format_analyzer: If True, use run_backup() for HarnessFormatAnalyzerAgent
        use_backup_corpus_matcher: If True, use run_backup() for CorpusMatcherAgent

    Returns:
        Tuple[Dict, Dict[str, List[str]]]: A tuple containing:
            - The format analysis results
            - The corpus matching results (mapping harness names to compatible categories)
    """

    # split the timeout 4:1
    format_timeout = int(timeout * 0.8)
    corpus_timeout = int(timeout * 0.2)

    # Step 1: Analyze harness formats
    format_analyzer = HarnessFormatAnalyzerAgent(
        model=model,
        project_bundle=project_bundle,
        timeout=format_timeout,
        cache_type=cache_type,
        cache_expire_time=cache_expire_time,
    )

    if use_backup_format_analyzer:
        format_analysis = await format_analyzer.run_backup()
    else:
        format_analysis = await format_analyzer.run()

    if not format_analysis:
        logger.error("Format analysis failed")
        return {}, {}

    # Step 2: Match with corpus categories
    corpus_matcher = CorpusMatcherAgent(
        model=model,
        project_bundle=project_bundle,
        available_categories=available_categories,
        timeout=corpus_timeout,
        cache_type=cache_type,
        cache_expire_time=cache_expire_time,
    )

    if use_backup_corpus_matcher:
        corpus_matches = await corpus_matcher.run_backup(format_analysis)
    else:
        corpus_matches = await corpus_matcher.run(format_analysis)

    return format_analysis, corpus_matches

async def fast_analyze_corpus_relevance(
    model: str,
    project_name: str,
    available_categories: List[str],
) -> Tuple[Dict, Dict[str, List[str]]]:
    """Fast analysis for corpus relevance using generate_text."""
    import json
    model_client = get_model("corpus_relevance", model)
    harness_format_prompt = BACKUP_HARNESS_FORMAT_ANALYSIS_PROMPT.format(project_name=project_name)
    format_analysis = await harness_format_analysis_backup(model_client, harness_format_prompt)
    corpus_matching_prompt = BACKUP_CORPUS_MATCHING_PROMPT.format(
        project_name=project_name,
        available_categories=json.dumps(available_categories),
        format_analysis=json.dumps(format_analysis)
    )
    corpus_matches = await corpus_matcher_backup(model_client, corpus_matching_prompt, available_categories)
    return format_analysis, corpus_matches
