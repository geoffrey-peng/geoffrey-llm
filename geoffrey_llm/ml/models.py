"""算法名到 sklearn 估计器的映射表。

每个算法名对应一个工厂函数,接受 random_state 返回 sklearn 估计器实例。
按分类/回归两种任务分别登记。
"""

from typing import Callable, Dict


def _random_forest_clf(random_state: int = 42):
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(n_estimators=100, random_state=random_state)


def _logistic_regression(random_state: int = 42):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(max_iter=1000, random_state=random_state)


def _svm(random_state: int = 42):
    from sklearn.svm import SVC
    return SVC(random_state=random_state, probability=True)


def _gradient_boosting_clf(random_state: int = 42):
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier(random_state=random_state)


def _random_forest_reg(random_state: int = 42):
    from sklearn.ensemble import RandomForestRegressor
    return RandomForestRegressor(n_estimators=100, random_state=random_state)


def _linear_regression(random_state: int = 42):
    from sklearn.linear_model import LinearRegression
    return LinearRegression()


def _gradient_boosting_reg(random_state: int = 42):
    from sklearn.ensemble import GradientBoostingRegressor
    return GradientBoostingRegressor(random_state=random_state)


#: 分类任务支持的算法
CLASSIFICATION_MODELS: Dict[str, Callable] = {
    "random_forest": _random_forest_clf,
    "logistic_regression": _logistic_regression,
    "svm": _svm,
    "gradient_boosting": _gradient_boosting_clf,
}

#: 回归任务支持的算法
REGRESSION_MODELS: Dict[str, Callable] = {
    "random_forest": _random_forest_reg,
    "linear_regression": _linear_regression,
    "gradient_boosting": _gradient_boosting_reg,
}


def get_model_factory(name: str, task: str) -> Callable:
    """按算法名 + 任务类型取工厂函数。

    Args:
        name: 算法名,如 "random_forest"
        task: "classification" 或 "regression"

    Returns:
        接受 random_state 返回 sklearn 估计器的工厂函数

    Raises:
        ValueError: 算法名或任务不支持
    """
    if task == "classification":
        table = CLASSIFICATION_MODELS
    elif task == "regression":
        table = REGRESSION_MODELS
    else:
        raise ValueError(f"不支持的任务类型: {task}。可选: classification, regression")

    if name not in table:
        available = ", ".join(table.keys())
        raise ValueError(f"不支持的算法: {name}(任务={task})。可选: {available}")
    return table[name]


def list_models(task: str) -> list[str]:
    """列出指定任务下支持的算法名。"""
    table = CLASSIFICATION_MODELS if task == "classification" else REGRESSION_MODELS
    return sorted(table.keys())
