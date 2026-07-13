"""评估报表格式化。

中英双语,默认中文。支持 Markdown 表格输出。
"""

from typing import Any, Dict, List


# 中英对照
_LABELS_CN = {
    "accuracy": "准确率",
    "precision": "精确率",
    "recall": "召回率",
    "f1": "F1",
    "support": "样本数",
    "macro_avg": "宏平均",
    "weighted_avg": "加权平均",
    "mse": "均方误差",
    "rmse": "均方根误差",
    "mae": "平均绝对误差",
    "r2": "R²",
}

_LABELS_EN = {
    "accuracy": "Accuracy",
    "precision": "Precision",
    "recall": "Recall",
    "f1": "F1",
    "support": "Support",
    "macro_avg": "Macro Avg",
    "weighted_avg": "Weighted Avg",
    "mse": "MSE",
    "rmse": "RMSE",
    "mae": "MAE",
    "r2": "R²",
}


def _pick_dict(chinese: bool) -> Dict[str, str]:
    return _LABELS_CN if chinese else _LABELS_EN


def format_classification_report(
    y_true: Any,
    y_pred: Any,
    chinese: bool = True,
) -> str:
    """生成分类评估报告(Markdown 表格)。

    含:准确率、每个类别的精确率/召回率/F1/样本数、宏平均、加权平均。
    """
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support

    labels_dict = _pick_dict(chinese)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )
    accuracy = accuracy_score(y_true, y_pred)

    # 取类别标签
    import numpy as np
    classes = np.unique(np.concatenate([np.asarray(y_true), np.asarray(y_pred)]))
    classes = sorted(classes.tolist())

    lines: List[str] = []
    lines.append(f"## {'分类评估报告' if chinese else 'Classification Report'}")
    lines.append("")
    lines.append(f"**{labels_dict['accuracy']}**: {accuracy:.4f}")
    lines.append("")
    lines.append(
        f"| {'类别' if chinese else 'Class'} "
        f"| {labels_dict['precision']} "
        f"| {labels_dict['recall']} "
        f"| {labels_dict['f1']} "
        f"| {labels_dict['support']} |"
    )
    lines.append("|---|---|---|---|---|")
    for i, c in enumerate(classes):
        lines.append(
            f"| {c} | {precision[i]:.4f} | {recall[i]:.4f} | {f1[i]:.4f} | {int(support[i])} |"
        )

    # 平均
    p_macro, r_macro, f1_macro, s_macro = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    p_w, r_w, f1_w, s_w = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    total_support = len(y_true)
    lines.append(
        f"| {labels_dict['macro_avg']} | {p_macro:.4f} | {r_macro:.4f} | {f1_macro:.4f} | {total_support} |"
    )
    lines.append(
        f"| {labels_dict['weighted_avg']} | {p_w:.4f} | {r_w:.4f} | {f1_w:.4f} | {total_support} |"
    )

    return "\n".join(lines)


def format_confusion_matrix(
    y_true: Any,
    y_pred: Any,
    chinese: bool = True,
) -> str:
    """生成混淆矩阵(Markdown 表格)。"""
    from sklearn.metrics import confusion_matrix
    import numpy as np

    cm = confusion_matrix(y_true, y_pred)
    classes = sorted(
        np.unique(np.concatenate([np.asarray(y_true), np.asarray(y_pred)])).tolist()
    )

    lines: List[str] = []
    lines.append(f"## {'混淆矩阵' if chinese else 'Confusion Matrix'}")
    lines.append("")
    header = f"| {'真实\\预测' if chinese else 'True\\Pred'} | " + " | ".join(str(c) for c in classes) + " |"
    sep = "|---" * (len(classes) + 1) + "|"
    lines.append(header)
    lines.append(sep)
    for i, r in enumerate(classes):
        row = f"| {r} | " + " | ".join(str(int(x)) for x in cm[i]) + " |"
        lines.append(row)

    return "\n".join(lines)


def format_regression_report(
    y_true: Any,
    y_pred: Any,
    chinese: bool = True,
) -> str:
    """生成回归评估报告(Markdown)。"""
    from sklearn.metrics import (
        mean_squared_error,
        mean_absolute_error,
        r2_score,
    )
    import numpy as np

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    labels_dict = _pick_dict(chinese)
    lines: List[str] = []
    lines.append(f"## {'回归评估报告' if chinese else 'Regression Report'}")
    lines.append("")
    lines.append(f"| {labels_dict['mse']} | {mse:.4f} |")
    lines.append(f"| {labels_dict['rmse']} | {rmse:.4f} |")
    lines.append(f"| {labels_dict['mae']} | {mae:.4f} |")
    lines.append(f"| {labels_dict['r2']} | {r2:.4f} |")

    return "\n".join(lines)
