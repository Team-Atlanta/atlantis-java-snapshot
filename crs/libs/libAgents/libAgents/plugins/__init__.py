import importlib
import inspect
from pathlib import Path

# Get the current directory
current_dir = Path(__file__).parent

# Dynamically import all modules in the current directory
for file in current_dir.glob("*.py"):
    if file.name != "__init__.py":
        module_name = file.stem
        module = importlib.import_module(f".{module_name}", package="libAgents.plugins")

        # Get all classes from the module
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                # Add the class to the current module's namespace
                globals()[name] = obj

# Get all classes that were added to the namespace
__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and not name.startswith("_")
]
