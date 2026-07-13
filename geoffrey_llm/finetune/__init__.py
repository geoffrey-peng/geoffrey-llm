"""大模型微调模块(开发中)。

基于 transformers / peft 封装 LoRA / QLoRA / Full-Param 微调流程,
配套数据集预处理、训练监控、模型合并、权重导出。

当前为占位,import 任一公共符号都会抛 NotImplementedError。

下一步规划:
- LoRATrainer / QLoRATrainer
- DatasetPreprocessor
- MergeAndExport 工具
"""

_DECLARED = ["LoRATrainer", "QLoRATrainer", "DatasetPreprocessor"]


def _not_ready(name: str):
    def _raise(*args, **kwargs):
        raise NotImplementedError(
            f"geoffrey_llm.finetune.{name} 暂未实现,微调模块开发中"
        )
    return _raise


LoRATrainer = _not_ready("LoRATrainer")
QLoRATrainer = _not_ready("QLoRATrainer")
DatasetPreprocessor = _not_ready("DatasetPreprocessor")

__all__ = _DECLARED
