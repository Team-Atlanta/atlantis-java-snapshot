import io
import sys
import time
import contextlib
import logging
from typing import Any, Optional, Dict, Callable
from .exec_base import Exec, ExecResult


logger = logging.getLogger(__name__)


class InProcessExec(Exec):
    """
    Executes a function from a Python script within the current process.
    """

    def __init__(
        self,
        script_content: str,
        function_name: str = "gen_one_seed",
    ):
        """
        Initializes the InProcessExec.

        Args:
            script_content: The content of the Python script to execute.
            function_name: Name of the function to call after script execution.
        """
        self.script_content = script_content
        self.function_name = function_name
        self.compiled_code = None
        self.exec_globals: Dict[str, Any] = {}
        self.target_function: Optional[Callable] = None
        
        # Execute the script once during initialization
        self._compile_and_execute_script()

    def _compile_and_execute_script(self):
        """Compiles and executes the script once to define functions."""
        try:
            # Compile the script
            self.compiled_code = compile(
                source=self.script_content, 
                filename="<anonymous>", 
                mode="exec",
                optimize=2
            )
            
            # Prepare globals for execution
            self.exec_globals = {
                "__name__": "__main__",
                "__file__": "<anonymous>",
                "sys": sys,
            }
            
            # Execute the script to define functions
            exec(self.compiled_code, self.exec_globals)
            
            # Check if the function exists
            if self.function_name not in self.exec_globals:
                raise NameError(f"Function '{self.function_name}' not found in script")
            
            # Store reference to the function
            self.target_function = self.exec_globals[self.function_name]
            if not callable(self.target_function):
                raise TypeError(f"'{self.function_name}' is not callable")
                
            logger.debug(f"Successfully compiled and loaded function '{self.function_name}'")
            
        except Exception as e:
            logger.error(f"Error initializing script: {e}")
            raise

    def exec(self, 
             script_args: list[str] = None,
             verbose: bool = False) -> ExecResult:
        """
        Calls the function defined in the script.

        Args:
            script_args: Command-line arguments to pass to the script.
            verbose: Whether to print additional debug information and measure execution time.

        Returns:
            ExecResult object containing success status, function result,
            captured output, and any error that occurred. When verbose=True,
            the exec_time field will contain timing information.
        """
        # Save original argv
        original_argv = sys.argv
        
        # Set up argv for the script
        current_argv = []
        if script_args:
            current_argv.extend(script_args)
        sys.argv = current_argv

        # Capture stdout
        output_capture = io.StringIO()
        result = None
        error = None
        exec_time = None
        
        # Start timing if verbose
        if verbose:
            start_time = time.time()
        
        try:
            # Call the function with stdout redirection
            with contextlib.redirect_stdout(output_capture):
                result = self.target_function()
                
        except Exception as e:
            error = e
            if verbose:
                logger.error(f"Error executing function: {e}", exc_info=True)
            else:
                logger.error(f"Error executing function: {e}")
        finally:
            # Restore original argv
            sys.argv = original_argv
            
            # Stop timing if verbose
            if verbose:
                end_time = time.time()
                exec_time = end_time - start_time
                logger.debug(f"Total execution time: {exec_time:.4f} seconds")
            
        # Get captured output
        output = output_capture.getvalue()
        
        # Return execution results as a dataclass instance
        success = error is None
        return ExecResult(
            success=success, 
            result=result, 
            output=output, 
            error=error,
            exec_time=exec_time
        )