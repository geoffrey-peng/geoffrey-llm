"""通用注册表。

子模块(ml/dl/geocode/finetune)各自维护一个 Registry 实例,
用来把字符串名映射到实现类(算法 / 工具 / 模型 provider 等)。
"""

from typing import Dict, Generic, Iterable, List, Type, TypeVar

from .errors import RegistryError

T = TypeVar("T")


class Registry(Generic[T]):
    """以名字为键的注册表,泛型 T 是被注册的类。

    用法:
        reg: Registry[BaseBackend] = Registry()
        reg.register("sklearn", SklearnBackend)
        cls = reg.get("sklearn")
    """

    def __init__(self) -> None:
        self._items: Dict[str, Type[T]] = {}

    def register(self, name: str, item: Type[T]) -> None:
        """注册一个实现类。重复注册抛 RegistryError。"""
        key = name.lower()
        if key in self._items:
            raise RegistryError(f"已注册同名项: {name}")
        self._items[key] = item

    def get(self, name: str) -> Type[T]:
        """按名取类。找不到抛 RegistryError,提示已注册项。"""
        key = name.lower()
        if key not in self._items:
            available = ", ".join(self._items.keys()) or "(空)"
            raise RegistryError(f"未注册的项: {name}。可选: {available}")
        return self._items[key]

    def list_names(self) -> List[str]:
        """列出所有已注册名。"""
        return sorted(self._items.keys())

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._items

    def __iter__(self) -> Iterable[str]:
        return iter(self._items)
