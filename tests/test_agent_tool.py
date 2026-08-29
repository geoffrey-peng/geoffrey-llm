"""Tests for the @tool decorator and FunctionTool."""

import asyncio

import pytest
from pydantic import ValidationError

from geoffrey_llm.agent import FunctionTool, tool


@tool
def add(a: int, b: int = 1) -> int:
    """加法工具。

    Args:
        a: 第一个加数
        b: 第二个加数,默认为 1
    """
    return a + b


@tool(name="custom_name", description="自定义描述")
async def greet(name: str) -> str:
    return f"你好,{name}"


def test_tool_schema_from_signature():
    assert add.name == "add"
    assert "加法" in add.description

    schema = add.get_schema()
    props = schema["properties"]
    assert props["a"]["type"] == "integer"
    assert props["a"]["description"] == "第一个加数"
    assert props["b"]["description"] == "第二个加数,默认为 1"
    assert set(schema["required"]) == {"a"}


def test_tool_call_sync_runs_in_thread():
    result = asyncio.run(add.call(add.validate_input({"a": 2, "b": 3})))
    assert result.success is True
    assert result.output == "5"


def test_tool_call_default_param():
    result = asyncio.run(add.call(add.validate_input({"a": 2})))
    assert result.success is True
    assert result.output == "3"


def test_tool_call_async_function():
    result = asyncio.run(greet.call(greet.validate_input({"name": "世界"})))
    assert result.success is True
    assert "你好,世界" in result.output


def test_tool_validation_rejects_bad_input():
    with pytest.raises(ValidationError):
        add.validate_input({"a": "not-a-number", "b": 1})


def test_tool_overrides():
    assert greet.name == "custom_name"
    assert greet.description == "自定义描述"


def test_tool_is_a_geocode_tool():
    # 与 geocode 内置工具同一接口,可被同一个循环执行
    from geoffrey_llm.geocode.tools.base import Tool

    assert isinstance(add, Tool)
    assert isinstance(add, FunctionTool)


def test_non_string_return_serialized_as_json():
    @tool
    def table(rows: int) -> dict:
        """返回示例字典。"""

        return {"count": rows}

    result = asyncio.run(table.call(table.validate_input({"rows": 3})))
    assert result.output == '{"count": 3}'


def test_chinese_docstring_section():
    @tool
    def 检索(query: str, top_n: int = 5) -> str:
        """按关键词检索文章。

        参数:
            query: 搜索关键词
            top_n: 返回条数
        """
        return "ok"

    schema = 检索.get_schema()
    assert schema["properties"]["query"]["description"] == "搜索关键词"
    assert schema["properties"]["top_n"]["description"] == "返回条数"
    assert "按关键词检索文章" in 检索.description
