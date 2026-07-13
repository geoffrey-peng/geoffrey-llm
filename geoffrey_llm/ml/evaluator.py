"""统一评估器。

提供分类 / 回归评估的中文/英文报表。
所有方法都是静态方法,可直接调用,不需要实例化。

用法:
    from geoffrey_llm.ml import Evaluator
    report = Evaluator.classification_report(y_true, y_pred, chinese=True)
    print(report)
"""

from typing import Any

from .report import (
    format_classification_report,
    format_confusion_matrix,
    format_regression_report,
)


class Evaluator:
    """模型评估工具(静态方法集合)。"""

    @staticmethod
    def classification_report(
        y_true: Any,
        y_pred: Any,
        chinese: bool = True,
    ) -> str:
        """分类评估报告(准确率 / 精确率 / 召回率 / F1 / 样本数 / 宏平均 / 加权平均)。"""
        return format_classification_report(y_true, y_pred, chinese=chinese)

    @staticmethod
    def confusion_matrix(
        y_true: Any,
        y_pred: Any,
        chinese: bool = True,
    ) -> str:
        """混淆矩阵(Markdown 表格)。"""
        return format_confusion_matrix(y_true, y_pred, chinese=chinese)

    @staticmethod
    def regression_report(
        y_true: Any,
        y_pred: Any,
        chinese: bool = True,
    ) -> str:
        """回归评估报告(MSE / RMSE / MAE / R²)。"""
        return format_regression_report(y_true, y_pred, chinese=chinese)

    @staticmethod
    def full_report(
        y_true: Any,
        y_pred: Any,
        task: str = "classification",
        chinese: bool = True,
    ) -> str:
        """生成完整报告(分类:报表+混淆矩阵;回归:报表)。"""
        if task == "classification":
            return (
                format_classification_report(y_true, y_pred, chinese=chinese)
                + "\n\n"
                + format_confusion_matrix(y_true, y_pred, chinese=chinese)
            )
        elif task == "regression":
            return format_regression_report(y_true, y_pred, chinese=chinese)
        else:
            raise ValueError(
                f"不支持的任务: {task}。可选: classification, regression"
            )
