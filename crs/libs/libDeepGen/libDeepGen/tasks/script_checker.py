import logging
from .task_base import Task
from libAgents.agents import DeepThinkAgent
from libAgents.utils import Project, get_model_by_weights
from libAgents.config import get_model
from libAgents.model import generate_text
from typing import Optional
from libDeepGen.executor import InProcessExec, ExecResult

logger = logging.getLogger(__name__)

class ScriptChecker:
    def __init__(self, model: str, script_content: str, max_iter: int=5):
        # NOTE: make sure we are testing gen_one_seed function
        self.model = model
        self.max_iter = max_iter
        self.original_script = script_content
        self.current_script = script_content
        script_fixing_models = {
            "gemini-2.5-pro": 40,
            "o4-mini": 40,
            "o3": 40,
        }
        if "claude" in model:
            self.model = get_model_by_weights(script_fixing_models)

    async def check(self, args: list[str] = None) -> Optional[str]:
        """
        Iteratively test and fix the script using LLM.
        Returns the fixed script if successful, None if failed after max_iter attempts.
        """
        for iteration in range(self.max_iter):
            logger.info(f"[ScriptChecker] Script checker iteration {iteration + 1}/{self.max_iter}")
            
            # Create executor with current script
            try:
                executor = InProcessExec(script_content=self.current_script)
            except Exception as e:
                logger.error(f"[ScriptChecker] Failed to initialize script: {e}")
                # Ask LLM to fix initialization/compilation error
                self.current_script = await self._fix_script_with_llm(
                    error_message=str(e),
                    error_type="compilation",
                    traceback_info=self._get_traceback()
                )
                continue
            
            # Try to execute the script
            try:
                result = executor.exec(script_args=args, verbose=True)

                if result.success:
                    logger.info(f"Script executed successfully on iteration {iteration + 1}")
                    # Verify the result is bytes
                    if result.result is not None and not isinstance(result.result, bytes):
                        logger.warning(f"Script returned {type(result.result)} instead of bytes")
                        self.current_script = await self._fix_script_with_llm(
                            error_message=f"gen_one_seed() returned {type(result.result).__name__} instead of bytes",
                            error_type="return_type",
                            output=result.output
                        )
                        continue
                    return self.current_script
                else:
                    # Script failed with runtime error
                    error_msg = str(result.error) if result.error else "Unknown error"
                    logger.warning(f"[ScriptChecker] Script execution failed: {error_msg}")
                    
                    self.current_script = await self._fix_script_with_llm(
                        error_message=error_msg,
                        error_type="runtime",
                        output=result.output,
                        traceback_info=self._get_traceback_from_error(result.error)
                    )
                    
            except Exception as e:
                logger.error(f"[ScriptChecker] Unexpected error during execution: {e}")
                self.current_script = await self._fix_script_with_llm(
                    error_message=str(e),
                    error_type="unexpected",
                    traceback_info=self._get_traceback()
                )
        
        logger.error(f"[ScriptChecker] Failed to fix script after {self.max_iter} iterations")
        return None
    
    def _get_traceback(self) -> str:
        """Get the current traceback as a string."""
        import traceback
        return traceback.format_exc()
    
    def _get_traceback_from_error(self, error: Optional[Exception]) -> str:
        """Extract traceback information from an error."""
        if error is None:
            return ""
        import traceback
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    
    async def _fix_script_with_llm(self, error_message: str, error_type: str, output: str = "", traceback_info: str = "") -> str:
        """Use LLM to fix the script based on the error."""
        
        prompt = f"""You are a Python expert helping to fix a fuzzing seed generator script.

The script must contain a function called `gen_one_seed()` that returns bytes for fuzzing.

Current script:
```python
{self.current_script}
```

Error type: {error_type}
Error message: {error_message}
"""
        
        if traceback_info:
            prompt += f"\nFull traceback:\n{traceback_info}\n"
        
        if output:
            prompt += f"\nScript output before error:\n{output}\n"
        
        prompt += """
Please fix the script to resolve this runtime error. Important requirements:
1. The script MUST have a function called `gen_one_seed()` that returns bytes
2. The function should generate different seeds each time it's called (use randomization)
3. Handle all necessary imports at the top of the script
4. Ensure the function can be called multiple times without state issues
5. Common fixes for runtime errors:
   - Add missing imports (random, os, struct, etc.)
   - Initialize any required global state
   - Handle file/directory operations properly
   - Convert string data to bytes using .encode() or b'' literals
   - Use proper random seed generation

Return ONLY the complete fixed Python script code, no explanations or markdown formatting.
"""
        
        try:
            # Get the model instance
            model = get_model("script_checker", self.model)
            
            # Generate the fixed script
            response = await generate_text(
                model=model,
                prompt=prompt,
                temperature=0.3,  # Low temperature for more deterministic fixes
            )
            
            # Extract the script from response
            fixed_script = response.object.strip()
            
            # Remove markdown code blocks if present
            if fixed_script.startswith("```python"):
                fixed_script = fixed_script[9:]  # Remove ```python
            elif fixed_script.startswith("```"):
                fixed_script = fixed_script[3:]  # Remove ```
            
            if fixed_script.endswith("```"):
                fixed_script = fixed_script[:-3]  # Remove trailing ```
            
            return fixed_script.strip()
            
        except Exception as e:
            logger.error(f"[ScriptChecker] Failed to get LLM fix: {e}")
            # Return the current script unchanged if LLM fails
            return self.current_script
