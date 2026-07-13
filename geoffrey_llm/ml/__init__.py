"""机器学习模块。

基于 scikit-learn 系算法提供统一训练 / 预测 / 评估 API。

安装:
    pip install geoffrey-llm[ml]

用法:
    from geoffrey_llm.ml import Trainer, Evaluator

    trainer = Trainer(task="classification", model_name="random_forest")
    trainer.fit(X_train, y_train)
    preds = trainer.predict(X_test)
    print(Evaluator.classification_report(y_test, preds, chinese=True))
"""

from .trainer import Trainer, Backend
from .evaluator import Evaluator
from .models import list_models
from .backends import BaseBackend, SklearnBackend

__all__ = [
    "Trainer",
    "Backend",
    "Evaluator",
    "BaseBackend",
    "SklearnBackend",
    "list_models",
]
