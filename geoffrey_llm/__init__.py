"""geoffrey-llm: A lightweight toolkit for LLM development.

顶层包只暴露元信息,各子模块独立 import:
    from geoffrey_llm.ml import Trainer, Evaluator
    from geoffrey_llm.geocode import REPL, BaseModel
    from geoffrey_llm.finetune import LoRATrainer  # 待实现
"""

import importlib.metadata as _metadata

__version__ = _metadata.version("geoffrey-llm")
__author__ = "Geoffrey"

__all__ = ["__version__", "__author__"]
