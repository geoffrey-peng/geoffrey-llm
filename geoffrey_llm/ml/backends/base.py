"""后端抽象基类。

每个 ml 后端(sklearn / lightgbm / xgboost)继承 BaseBackend,
实现 fit / predict / save / load 四个方法。
Trainer 内部路由到具体后端,对外暴露统一 API。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ...common.errors import BackendError


class BaseBackend(ABC):
    """所有 ml 后端的抽象基类。"""

    #: 后端名,子类必须覆盖(如 "sklearn" / "lightgbm")
    name: str = "base"

    @abstractmethod
    def fit(self, X: Any, y: Any) -> None:
        """在训练数据上拟合模型。"""

    @abstractmethod
    def predict(self, X: Any) -> Any:
        """对测试数据做预测,返回预测标签或值。"""

    @abstractmethod
    def save(self, path: str) -> None:
        """把模型序列化到文件。"""

    @abstractmethod
    def load(self, path: str) -> None:
        """从文件反序列化模型,替换当前后端内部模型。"""

    @abstractmethod
    def get_model(self) -> Any:
        """取出底层原始模型对象(供高级用户直接操作)。"""

    @abstractmethod
    def supported_models(self) -> list[str]:
        """列出此后端支持的算法名。"""

    def _ensure_model_set(self) -> None:
        """公用前置检查:模型必须已 fit。"""
        if self.get_model() is None:
            raise BackendError(f"后端 {self.name} 尚未训练,先调用 fit()")
