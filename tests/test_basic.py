import re

from geoffrey_llm import __author__, __version__


def test_version_is_semver():
    # 版本号随发布演进,这里只锁格式,避免每次发版都改测试
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)


def test_author():
    assert __author__ == "Geoffrey"
