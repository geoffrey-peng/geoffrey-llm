from geoffrey_llm import __author__, __version__


def test_version():
    assert __version__ == "0.2.0"


def test_author():
    assert __author__ == "Geoffrey"
