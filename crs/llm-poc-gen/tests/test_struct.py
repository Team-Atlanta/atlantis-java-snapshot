import sys
from pathlib import Path

import pytest

from vuli.struct import CodeLocation

test_dir: Path = Path(__file__).parent
root_dir: Path = test_dir.parent
sys.path.append(str(root_dir))


def test_code_location():
    loc1 = CodeLocation("a", 1, 2)
    assert loc1.path == "a"
    assert loc1.line == 1
    assert loc1.column == 2

    loc2 = CodeLocation("a", 1)
    assert loc2.path == "a"
    assert loc2.line == 1
    assert loc2.column == -1

    loc3 = CodeLocation.create("a:1:2")
    assert loc3.path == "a"
    assert loc3.line == 1
    assert loc3.column == 2

    loc4 = CodeLocation.create("a:1")
    assert loc4.path == "a"
    assert loc4.line == 1
    assert loc4.column == -1

    with pytest.raises(ValueError):
        CodeLocation.create("a")

    with pytest.raises(ValueError):
        CodeLocation.create("a:b")

    with pytest.raises(ValueError):
        CodeLocation.create("a:1:2:3")
