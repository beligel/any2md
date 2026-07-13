"""Unit-тесты для any2md CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest

from any2md.cli import main


def test_list_formats_exits_without_input(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--list-formats"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert ".txt" in captured.out
    assert ".pdf" in captured.out


def test_stdout_output(tmp_path, capsys):
    src = tmp_path / "hello.txt"
    src.write_text("Stdout test")
    with pytest.raises(SystemExit) as exc_info:
        main([str(src), "-o", "-"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Stdout test" in captured.out


def test_no_input_prints_usage(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Ошибка" in captured.err or "usage" in captured.err
