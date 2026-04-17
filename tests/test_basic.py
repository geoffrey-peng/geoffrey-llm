from geoffrey_llm import placeholder, __version__


def test_version():
    assert __version__ == "0.0.1"


def test_placeholder():
    result = placeholder()
    assert "under development" in result