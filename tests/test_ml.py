"""geoffrey_llm.ml 模块单元测试。

依赖 scikit-learn,跑前确保 `pip install -e .[ml,dev]`。
"""

import tempfile
from pathlib import Path

import pytest

from geoffrey_llm.ml import Trainer, Evaluator, Backend, list_models


# ---- 公共 fixtures ----

@pytest.fixture
def iris_split():
    from sklearn.datasets import load_iris
    X, y = load_iris(return_X_y=True)
    return X[:120], X[120:], y[:120], y[120:]


@pytest.fixture
def regression_split():
    from sklearn.datasets import make_regression
    X, y = make_regression(n_samples=200, n_features=10, noise=0.1, random_state=42)
    return X[:160], X[160:], y[:160], y[160:]


# ---- Trainer 基础 ----

def test_trainer_classification_fit_predict(iris_split):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    assert len(preds) == len(y_test)
    assert t.get_backend() is not None


def test_trainer_returns_self_on_fit(iris_split):
    X_train, _, y_train, _ = iris_split
    t = Trainer()
    result = t.fit(X_train, y_train)
    assert result is t


def test_trainer_default_backend_is_sklearn():
    t = Trainer()
    assert t.backend_name == "sklearn"


def test_invalid_task_raises():
    from geoffrey_llm.common.errors import BackendError
    with pytest.raises(BackendError):
        Trainer(task="invalid_task")


def test_invalid_model_name_raises():
    with pytest.raises(ValueError):
        Trainer(task="classification", model_name="does_not_exist")


def test_predict_without_fit_raises():
    from geoffrey_llm.common.errors import BackendError
    t = Trainer()
    with pytest.raises(BackendError):
        t.predict([[1, 2, 3]])


# ---- 各算法 ----

@pytest.mark.parametrize("model_name", list_models("classification"))
def test_all_classification_models(iris_split, model_name):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name=model_name)
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    assert len(preds) == len(y_test)


@pytest.mark.parametrize("model_name", list_models("regression"))
def test_all_regression_models(regression_split, model_name):
    X_train, X_test, y_train, y_test = regression_split
    t = Trainer(task="regression", model_name=model_name)
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    assert len(preds) == len(y_test)


# ---- predict_proba ----

def test_predict_proba_classification(iris_split):
    X_train, X_test, y_train, _ = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    proba = t.predict_proba(X_test)
    assert proba.shape[0] == len(X_test)


def test_predict_proba_regression_raises(regression_split):
    X_train, _, y_train, _ = regression_split
    t = Trainer(task="regression", model_name="linear_regression")
    t.fit(X_train, y_train)
    from geoffrey_llm.common.errors import BackendError
    with pytest.raises(BackendError):
        t.predict_proba(X_train)


# ---- 持久化 ----

def test_save_and_load_roundtrip(iris_split):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds_before = t.predict(X_test)

    with tempfile.TemporaryDirectory() as d:
        path = str(Path(d) / "model.pkl")
        t.save(path)
        t2 = Trainer.load(
            path,
            backend=Backend.SKLEARN,
            task="classification",
            model_name="random_forest",
        )
        preds_after = t2.predict(X_test)

    assert list(preds_before) == list(preds_after)


# ---- Evaluator ----

def test_classification_report_chinese(iris_split):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    report = Evaluator.classification_report(y_test, preds, chinese=True)
    assert "分类评估报告" in report
    assert "准确率" in report
    assert "宏平均" in report


def test_classification_report_english(iris_split):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    report = Evaluator.classification_report(y_test, preds, chinese=False)
    assert "Classification Report" in report
    assert "Accuracy" in report


def test_confusion_matrix(iris_split):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    cm = Evaluator.confusion_matrix(y_test, preds, chinese=True)
    assert "混淆矩阵" in cm


def test_regression_report(regression_split):
    X_train, X_test, y_train, y_test = regression_split
    t = Trainer(task="regression", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    report = Evaluator.regression_report(y_test, preds, chinese=True)
    assert "回归评估报告" in report
    assert "均方误差" in report
    assert "R²" in report


def test_full_report_classification(iris_split):
    X_train, X_test, y_train, y_test = iris_split
    t = Trainer(task="classification", model_name="random_forest")
    t.fit(X_train, y_train)
    preds = t.predict(X_test)
    report = Evaluator.full_report(y_test, preds, task="classification", chinese=True)
    assert "分类评估报告" in report
    assert "混淆矩阵" in report


# ---- list_models ----

def test_list_models_classification():
    models = list_models("classification")
    assert "random_forest" in models
    assert "svm" in models


def test_list_models_regression():
    models = list_models("regression")
    assert "linear_regression" in models
