import os
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
from litellm import *   # Import all public components
from .main import completion
from .models import get_tokens_per_minute, get_requests_per_minute

# Import/Export private components
import litellm
names = [name for name in dir(litellm) if name.startswith('_')]
globals().update({name: getattr(litellm, name) for name in names})