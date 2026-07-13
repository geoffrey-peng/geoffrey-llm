"""统一训练器。

对外暴露一致的 fit / predict / save / load 接口,
内部按 backend 名路由到具体后端实现。

用法:
    from geoffrey_llm.ml import Trainer
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    t.save("model.pkl")
"""

from enum import Enum
from typing import Any, Optional

from ..common.errors import BackendError
from ..common.registry import Registry
from .backends.base import BaseBackend
from .backends.sklearn_backend import SklearnBackend


class Backend(str, Enum):
    """后端枚举。MVP 只支持 sklearn,后续加 lightgbm / xgboost。"""

    SKLEARN = "sklearn"


#: 后端注册表
_backend_registry: Registry[BaseBackend] = Registry()
_backend_registry.register("sklearn", SklearnBackend)


class Trainer:
    """统一训练器,封装各后端。

    Args:
        backend: Backend 枚举,默认 Backend.SKLEARN
        task: "classification" 或 "regression"
        model_name: 算法名,如 "random_forest"(具体可选见 backend.supported_models())
        random_state: 随机种子,默认 42
    """

    def __init__(
        self,
        backend: Backend = Backend.SKLEARN,
        task: str = "classification",
        model_name: str = "random_forest",
        random_state: int = 42,
    ) -> None:
        if task not in ("classification", "regression"):
            raise BackendError(
                f"不支持的任务: {task}。可选: classification, regression"
            )

        backend_name = backend.value if isinstance(backend, Backend) else str(backend)
        backend_cls = _backend_registry.get(backend_name)

        self.backend_name = backend_name
        self.task = task
        self.model_name = model_name
        self.random_state = random_state
        self._backend: BaseBackend = backend_cls(
            model_name=model_name,
            task=task,
            random_state=random_state,
        )

    def fit(self, X: Any, y: Any) -> "Trainer":
        """训练模型,返回 self 支持链式调用。"""
        self._backend.fit(X, y)
        return self

    def predict(self, X: Any) -> Any:
        """预测。"""
        return self._backend.predict(X)

    def predict_proba(self, X: Any) -> Any:
        """分类任务的概率预测。回归任务抛错。"""
        return self._backend.predict_proba(X)

    def save(self, path: str) -> None:
        """保存模型到文件。"""
        self._backend.save(path)

    @classmethod
    def load(
        cls,
        path: str,
        backend: Backend = Backend.SKLEARN,
        task: str = "classification",
        model_name: str = "random_forest",
    ) -> "Trainer":
        """从文件加载模型。

        需要提供与保存时一致的 backend / task / model_name,
        用于正确构造 Trainer 对象。
        """
        trainer = cls(
            backend=backend,
            task=task,
            model_name=model_name,
        )
        trainer._backend.load(path)
        return trainer

    def get_backend(self) -> BaseBackend:
        """获取底层后端对象,供高级用户操作。"""
        return self._backend

    def supported_models(self) -> list[str]:
        """列出当前后端 + 任务下支持的算法名。"""
        return self._backend.supported_models()
