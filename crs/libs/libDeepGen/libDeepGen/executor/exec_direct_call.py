import io
import sys
import time
import importlib.util
import contextlib
import logging
from .exec_base import Exec, ExecResult


logger = logging.getLogger(__name__)


class DirectCallExec(Exec):
    """
    Executes a function from a Python script by loading it as a module and calling directly.
    """

    def __init__(
        self,
        script_content: str,
        function_name: str = "gen_one_seed",
        module_name: str = "dynamic_module"
    ):
        """
        Initializes the DirectCallExec.

        Args:
            script_content: The content of the Python script to execute.
            function_name: Name of the function to call after script execution.
            module_name: Name to use for the dynamically created module.
        """
        self.script_content = script_content
        self.function_name = function_name
        self.module_name = module_name
        self.module = None
        self.target_function = None
        
        # Load the script as a module during initialization
        self._load_as_module()

    def _load_as_module(self):
        """Loads the script content as a Python module."""
        try:
            # Create module spec
            spec = importlib.util.spec_from_loader(
                self.module_name, 
                loader=None
            )
            
            # Create the module
            self.module = importlib.util.module_from_spec(spec)
            
            # Add module to sys.modules to handle potential imports within the script
            sys.modules[self.module_name] = self.module
            
            # Set __name__ and __file__ attributes
            self.module.__name__ = "__main__"
            self.module.__file__ = "<dynamic>"
            
            # Execute the code within module's namespace
            exec(self.script_content, self.module.__dict__)
            
            # Get the target function
            if not hasattr(self.module, self.function_name):
                raise NameError(f"Function '{self.function_name}' not found in script")
                
            self.target_function = getattr(self.module, self.function_name)
            if not callable(self.target_function):
                raise TypeError(f"'{self.function_name}' is not callable")
                
            logger.debug(f"Successfully loaded function '{self.function_name}' from dynamic module")
            
        except Exception as e:
            logger.error(f"Error loading module: {e}")
            raise

    def exec(self, 
             script_args: list[str] = None,
             verbose: bool = False) -> ExecResult:
        """
        Calls the function from the dynamically loaded module.

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
