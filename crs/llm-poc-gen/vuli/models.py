from abc import ABC, abstractmethod
from typing import Optional


class LLMModel(ABC):
    @abstractmethod
    def cost(self, input, output):
        pass

    @property
    @abstractmethod
    def name(self):
        pass


class Grok3(LLMModel):
    def cost(self, input, output):
        return input * 0.000003 + output * 0.000015

    @property
    def name(self):
        return "grok-3"


class Gemini25Pro(LLMModel):
    def cost(self, input, output):
        return (
            input * 0.00000125 + output * 0.00001
            if input < 200000
            else input * 0.0000025 + output * 0.000015
        )

    @property
    def name(self):
        return "gemini-2.5-pro"


class ClaudeSonnet4(LLMModel):
    def cost(self, input, output):
        return input * 0.000003 + output * 0.000015

    @property
    def name(self):
        return "claude-sonnet-4-20250514"


class ClaudeOpus4(LLMModel):
    def cost(self, input, output):
        return input * 0.000015 + output * 0.000075

    @property
    def name(self):
        return "claude-opus-4-20250514"


class GPT41(LLMModel):
    def cost(self, input, output):
        return input * 0.000002 + output * 0.000008

    @property
    def name(self):
        return "gpt-4.1"


class O3(LLMModel):
    def cost(self, input, output):
        return input * 0.000002 + output * 0.000008

    @property
    def name(self):
        return "o3"


def get_model(name: str) -> Optional[LLMModel]:
    models: dict[str, LLMModel] = {
        "gemini-2.5-pro": Gemini25Pro,
        "claude-sonnet-4-20250514": ClaudeSonnet4,
        "claude-opus-4-20250514": ClaudeOpus4,
        "gpt-4.1": GPT41,
        "grok-3": Grok3,
        "o3": O3,
    }

    if name in models:
        return models[name]
    return None
