# Wrapping Libraries

- currently re-exporting everything from `openai` (not done yet...). Is there a better way?
- for fixing the LiteLLM issues, maybe just fork? Needs investigation.

# AIxCC LiteLLM

- specifying `model` in LiteLLM API is broken. Workaround is to specify it in OpenAI API
- specifying `temperature` in OpenAI completions gives `RateLimitError`
