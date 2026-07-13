"""通用配置基类。

子模块的 Config dataclass 继承它,获得 from_dict / validate 通用能力。
"""

from dataclasses import dataclass, fields
from typing import Any, Dict, Type, TypeVar

from .errors import ConfigError

C = TypeVar("C", bound="BaseConfig")


@dataclass
class BaseConfig:
    """所有配置类的基类。继承后用 @dataclass 添加字段即可。"""

    @classmethod
    def from_dict(cls: Type[C], data: Dict[str, Any]) -> C:
        """从字典构造配置。字典中多余的键会被忽略,缺失的必填字段抛 ConfigError。"""
        import dataclasses

        valid_names = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_names}

        try:
            return cls(**filtered)
        except TypeError as e:
            raise ConfigError(f"配置缺少必填字段或字段类型不对: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """配置序列化为字典。"""
        import dataclasses

        return dataclasses.asdict(self)

    def validate(self) -> None:
        """子类可重写,做跨字段一致性校验。默认不做任何检查。"""
        return None
