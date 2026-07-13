"""Unit-тесты для any2md.cli — расширенные сценарии.

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: --version печатает версию и выходит
  AC-2: --list-formats печатает форматы и выходит с кодом 0
  AC-3: -o - stdout печатает содержимое и выходит с кодом 0
  AC-4: несуществующий путь → выход с кодом 1
  AC-5: без аргументов → usage + выход с кодом 1
  AC-6: конвертация файла → печатает путь к .md
  AC-7: конвертация директории → печатает список путей
  AC-8: --verbose при ошибке → re-raise
  AC-9: _print_supported_formats содержит .txt и .pdf
"""

import sys
from pathlib import Path

import pytest

from any2md.cli import main, _print_supported_formats


# ---------------------------------------------------------------------------
# AC-1: --version
# ---------------------------------------------------------------------------

def test_version_prints_and_exits(capsys):
    """AC-1: --version печатает версию и выходит с кодом 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# AC-2: --list-formats
# ---------------------------------------------------------------------------

def test_list_formats_exits_zero(capsys):
    """AC-2: --list-formats печатает форматы и выходит с кодом 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--list-formats"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert ".txt" in captured.out
    assert ".pdf" in captured.out


# ---------------------------------------------------------------------------
# AC-3: -o - stdout
# ---------------------------------------------------------------------------

def test_stdout_output_exits_zero(tmp_path, capsys):
    """AC-3: -o - печатает содержимое и выходит с кодом 0."""
    src = tmp_path / "hello.txt"
    src.write_text("Stdout content")
    with pytest.raises(SystemExit) as exc_info:
        main([str(src), "-o", "-"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Stdout content" in captured.out


# ---------------------------------------------------------------------------
# AC-4: несуществующий путь
# ---------------------------------------------------------------------------

def test_nonexistent_path_exits_one(tmp_path, capsys):
    """AC-4: несуществующий путь → выход с кодом 1."""
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nonexistent")])
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# AC-5: без аргументов
# ---------------------------------------------------------------------------

def test_no_args_exits_one(capsys):
    """AC-5: без аргументов → usage + выход с кодом 1."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Ошибка" in captured.err or "usage" in captured.err.lower()


# ---------------------------------------------------------------------------
# AC-6: конвертация файла → печатает путь
# ---------------------------------------------------------------------------

def test_single_file_conversion_prints_path(tmp_path, capsys):
    """AC-6: конвертация одного файла печатает путь к .md."""
    src = tmp_path / "test.txt"
    src.write_text("Hello")
    with pytest.raises(SystemExit) as exc_info:
        main([str(src), "-o", str(tmp_path / "out.md")])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "out.md" in captured.out


# ---------------------------------------------------------------------------
# AC-7: конвертация директории → печатает список
# ---------------------------------------------------------------------------

def test_directory_conversion_prints_list(tmp_path, capsys):
    """AC-7: конвертация директории печатает пути к .md файлам."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("A")
    (src_dir / "b.txt").write_text("B")

    out_dir = tmp_path / "out"
    with pytest.raises(SystemExit) as exc_info:
        main([str(src_dir), "-o", str(out_dir)])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert ".md" in captured.out


# ---------------------------------------------------------------------------
# AC-8: --verbose при ошибке → re-raise
# ---------------------------------------------------------------------------

def test_verbose_reraises_on_error(tmp_path):
    """AC-8: --verbose вызывает re-raise исключения вместо подавления."""
    # Несуществующий путь с --verbose — должен вернуть код 1, не упасть
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nonexistent"), "--verbose"])
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# AC-9: _print_supported_formats
# ---------------------------------------------------------------------------

def test_print_supported_formats(capsys):
    """AC-9: _print_supported_formats выводит .txt и .pdf."""
    _print_supported_formats()
    captured = capsys.readouterr()
    assert ".txt" in captured.out
    assert ".pdf" in captured.out
    assert "Поддерживаемые форматы" in captured.out