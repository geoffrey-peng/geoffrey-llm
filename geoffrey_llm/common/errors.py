"""中文友好的错误基类。

所有模块抛出的异常都继承自 `GeoffreyError`,信息一律中文。
这是 SDK "中文友好" 策略的统一入口。
"""


class GeoffreyError(Exception):
    """所有 geoffrey-llm 异常的基类。"""


class ConfigError(GeoffreyError):
    """配置错误(参数缺失、类型不对、值非法等)。"""


class BackendError(GeoffreyError):
    """后端错误(算法不支持、后端未安装、训练失败等)。"""


class RegistryError(GeoffreyError):
    """注册表错误(重复注册、未注册、查找不到等)。"""
