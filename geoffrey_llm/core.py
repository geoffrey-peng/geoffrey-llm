"""Core module - placeholder for future implementation"""


def placeholder():
    """Placeholder function, will be replaced with actual features."""
    return "geoffrey-llm is under development. Stay tuned!"


class LLMConfig:
    """Configuration class for LLM operations."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
    
    def info(self):
        return f"Config for {self.model_name}"