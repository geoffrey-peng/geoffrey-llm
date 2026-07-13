"""sklearn 后端实现。

封装 sklearn 系算法,提供 fit / predict / save / load 统一接口。
"""

from typing import Any, Optional

from ...common.errors import BackendError
from ..models import get_model_factory, list_models
from .base import BaseBackend


class SklearnBackend(BaseBackend):
    """scikit-learn 后端。"""

    name = "sklearn"

    def __init__(
        self,
        model_name: str = "random_forest",
        task: str = "classification",
        random_state: int = 42,
    ) -> None:
        self.model_name = model_name
        self.task = task
        self.random_state = random_state
        self._model: Optional[Any] = None
        self._is_fitted = False

        factory = get_model_factory(model_name, task)
        self._factory = factory
        self._model = factory(random_state)

    def fit(self, X: Any, y: Any) -> None:
        """在 (X, y) 上训练模型。"""
        self._model.fit(X, y)
        self._is_fitted = True

    def predict(self, X: Any) -> Any:
        """预测 X 的标签或值。"""
        self._ensure_model_set()
        if not self._is_fitted:
            raise BackendError("模型尚未训练,请先调用 fit()")
        return self._model.predict(X)

    def predict_proba(self, X: Any) -> Any:
        """分类任务专用:返回概率矩阵。回归任务抛 BackendError。"""
        if self.task != "classification":
            raise BackendError(f"predict_proba 仅用于分类任务,当前 task={self.task}")
        self._ensure_model_set()
        if not self._is_fitted:
            raise BackendError("模型尚未训练,请先调用 fit()")
        if not hasattr(self._model, "predict_proba"):
            raise BackendError(
                f"算法 {self.model_name} 不支持 predict_proba "
                f"(可能是 SVM 未启用 probability=True,或算法本身不支持)"
            )
        return self._model.predict_proba(X)

    def save(self, path: str) -> None:
        """序列化模型到文件。优先用 joblib,兜底 pickle。"""
        self._ensure_model_set()
        try:
            import joblib
            joblib.dump(self._model, path)
        except ImportError:
            import pickle
            with open(path, "wb") as f:
                pickle.dump(self._model, f)

    def load(self, path: str) -> None:
        """从文件加载模型,替换当前模型对象。"""
        try:
            import joblib
            self._model = joblib.load(path)
        except ImportError:
            import pickle
            with open(path, "rb") as f:
                self._model = pickle.load(f)
        self._is_fitted = True

    def get_model(self) -> Any:
        """返回底层 sklearn 估计器。"""
        return self._model

    def supported_models(self) -> list[str]:
        """返回当前任务下 sklearn 后端支持的算法名。"""
        return list_models(self.task)
