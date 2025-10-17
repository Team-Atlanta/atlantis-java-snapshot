from pathlib import Path

from vuli.cp import CP


def test_set_diff_path():
    CP()._diff_path = None

    # CP()._diff_path will set if the given path is an existing file
    diff_path: Path = Path(__file__)
    CP()._set_diff_path(diff_path)
    assert CP()._diff_path == diff_path


def test_set_diff_path_invalid():
    CP()._diff_path = None

    # CP()._diff_path will not set if the given path is not a file
    diff_path: Path = Path("")
    CP()._set_diff_path(diff_path)
    assert CP()._diff_path is None

    # CP()._diff_path will not set if the given path is not exist
    diff_path: Path = Path(__file__, "fake")
    CP()._set_diff_path(diff_path)
    assert CP()._diff_path is None
