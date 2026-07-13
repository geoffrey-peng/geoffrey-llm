"""深度学习模块(开发中)。

基于 PyTorch 封装神经网络训练与推理,提供与 ml 模块对称的 API。
当前为占位,import 任一公共符号都会抛 NotImplementedError。

下一步规划:
- CNN / RNN / Transformer 基础架构
- 自定义层与训练循环封装
- 与 ml.Trainer 对称的 DLTrainer
"""

_DECLARED = ["Trainer", "Evaluator", "Backend"]


def _not_ready(name: str):
    def _raise(*args, **kwargs):
        raise NotImplementedError(
            f"geoffrey_llm.dl.{name} 暂未实现,深度学习模块开发中"
        )
    return _raise


Trainer = _not_ready("Trainer")
Evaluator = _not_ready("Evaluator")
Backend = _not_ready("Backend")

__all__ = _DECLARED
