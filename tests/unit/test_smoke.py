import platform

import shieldz


def test_package_imports():
    assert shieldz.__version__


def test_python_is_312():
    assert platform.python_version_tuple()[:2] == ("3", "12")
