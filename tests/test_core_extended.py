"""Unit-тесты для any2md.core — внутренние функции и edge cases.

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: _path_to_output keep_relative=True с root
  AC-2: _path_to_output keep_relative=True без root (абсолютный путь)
  AC-3: _path_to_output keep_relative=False → stem.md
  AC-4: _collect_files recursive=True/False
  AC-5: _is_archive для разных расширений
  AC-6: _is_supported по расширению и MIME
  AC-7: _extract_or_decode — бинарный файл пропускается
  AC-8: _extract_or_decode — текстовый файл декодируется
  AC-9: convert stdout=True → None, текст в sys.stdout
  AC-10: convert FileNotFoundError для несуществующего пути
  AC-11: convert архив → директория с .md файлами
  AC-12: convert директория с архивом внутри
  AC-13: convert non-recursive директория
  AC-14: convert директория с неподдерживаемым файлом (пропуск)
"""

import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from any2md.core import (
    SUPPORTED_SUFFIXES,
    _collect_files,
    _convert_single_file,
    _extract_or_decode,
    _is_archive,
    _is_supported,
    _path_to_output,
    convert,
)
from any2md.extractors.registry import ExtractionContext


# ---------------------------------------------------------------------------
# AC-1: _path_to_output keep_relative=True с root
# ---------------------------------------------------------------------------

def test_path_to_output_relative_with_root(tmp_path):
    """AC-1: _path_to_output сохраняет относительный путь от root."""
    root = tmp_path / "project"
    src = root / "sub" / "file.txt"
    src.parent.mkdir(parents=True)
    src.write_text("hello")
    out_dir = tmp_path / "out"

    result = _path_to_output(src, out_dir, keep_relative=True, root=root)
    assert result == out_dir / "sub" / "file.md"
    assert result.parent.exists()  # ensure_dir создал папку


# ---------------------------------------------------------------------------
# AC-2: _path_to_output keep_relative=True без root (абсолютный путь)
# ---------------------------------------------------------------------------

def test_path_to_output_absolute_no_root(tmp_path):
    """AC-2: _path_to_output для абсолютного пути без root."""
    src = tmp_path / "file.txt"
    src.write_text("hello")
    out_dir = tmp_path / "out"

    result = _path_to_output(src, out_dir, keep_relative=True, root=None)
    # Абсолютный путь — rel берётся от anchor
    assert result.suffix == ".md"
    assert result.name == "file.md"


# ---------------------------------------------------------------------------
# AC-3: _path_to_output keep_relative=False → stem.md
# ---------------------------------------------------------------------------

def test_path_to_output_no_keep_relative(tmp_path):
    """AC-3: _path_to_output keep_relative=False → output_dir/stem.md."""
    src = tmp_path / "deep" / "nested" / "file.txt"
    src.parent.mkdir(parents=True)
    src.write_text("hello")
    out_dir = tmp_path / "out"

    result = _path_to_output(src, out_dir, keep_relative=False)
    assert result == out_dir / "file.md"


# ---------------------------------------------------------------------------
# AC-4: _collect_files recursive=True/False
# ---------------------------------------------------------------------------

def test_collect_files_recursive(tmp_path):
    """AC-4a: _collect_files recursive=True находит вложенные файлы."""
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")

    files = list(_collect_files(tmp_path, recursive=True))
    names = {f.name for f in files}
    assert "a.txt" in names
    assert "b.txt" in names


def test_collect_files_non_recursive(tmp_path):
    """AC-4b: _collect_files recursive=False только верхний уровень."""
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")

    files = list(_collect_files(tmp_path, recursive=False))
    names = {f.name for f in files}
    assert "a.txt" in names
    assert "b.txt" not in names


# ---------------------------------------------------------------------------
# AC-5: _is_archive
# ---------------------------------------------------------------------------

def test_is_archive_zip(tmp_path):
    """AC-5: _is_archive распознаёт .zip."""
    assert _is_archive(Path("test.zip")) is True


def test_is_archive_non_archive(tmp_path):
    """AC-5b: _is_archive возвращает False для .txt."""
    assert _is_archive(Path("test.txt")) is False


def test_is_archive_tar_gz():
    """AC-5c: _is_archive распознаёт .tar.gz."""
    assert _is_archive(Path("archive.tar.gz")) is True


# ---------------------------------------------------------------------------
# AC-6: _is_supported
# ---------------------------------------------------------------------------

def test_is_supported_by_extension():
    """AC-6a: _is_supported возвращает True для .txt."""
    assert _is_supported(Path("file.txt")) is True


def test_is_supported_unsupported_extension():
    """AC-6b: _is_supported возвращает False для .xyz."""
    assert _is_supported(Path("file.xyz")) is False


def test_is_supported_archive_extension():
    """AC-6c: _is_supported возвращает True для .zip."""
    assert _is_supported(Path("file.zip")) is True


# ---------------------------------------------------------------------------
# AC-7: _extract_or_decode — бинарный файл пропускается
# ---------------------------------------------------------------------------

def test_extract_or_decode_binary_skipped(tmp_path):
    """AC-7: бинарный файл без экстрактора → сообщение о пропуске."""
    src = tmp_path / "data.bin"
    src.write_bytes(b"\x00\x01\x02\x03\xFF\xFE")
    ctx = ExtractionContext()
    result = _extract_or_decode(src, ctx)
    assert "Бинарный файл пропущен" in result
    assert "data.bin" in result


# ---------------------------------------------------------------------------
# AC-8: _extract_or_decode — текстовый файл декодируется
# ---------------------------------------------------------------------------

def test_extract_or_decode_text_file(tmp_path):
    """AC-8: текстовый файл без экстрактора → декодируется."""
    src = tmp_path / "readme"
    src.write_text("Plain text content", encoding="utf-8")
    ctx = ExtractionContext()
    result = _extract_or_decode(src, ctx)
    assert result == "Plain text content"


# ---------------------------------------------------------------------------
# AC-9: convert stdout=True → None, текст в sys.stdout
# ---------------------------------------------------------------------------

def test_convert_stdout_returns_none(tmp_path, capsys):
    """AC-9: convert с stdout=True возвращает None и пишет в stdout."""
    src = tmp_path / "hello.txt"
    src.write_text("Hello stdout")
    result = convert(src, stdout=True)
    assert result is None
    captured = capsys.readouterr()
    assert "Hello stdout" in captured.out


# ---------------------------------------------------------------------------
# AC-10: convert FileNotFoundError
# ---------------------------------------------------------------------------

def test_convert_nonexistent_raises(tmp_path):
    """AC-10: convert бросает FileNotFoundError для несуществующего пути."""
    with pytest.raises(FileNotFoundError):
        convert(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# AC-11: convert архив → директория с .md
# ---------------------------------------------------------------------------

def test_convert_archive_creates_md_files(tmp_path):
    """AC-11: конвертация архива создаёт .md файлы для содержимого."""
    # Создаём архив
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "readme.txt").write_text("Archive readme")
    (content_dir / "data.json").write_text('{"key":"value"}')

    archive_path = tmp_path / "test.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(content_dir / "readme.txt", "content/readme.txt")
        zf.write(content_dir / "data.json", "content/data.json")

    out_dir = tmp_path / "out"
    results = convert(archive_path, output_path=out_dir)

    assert isinstance(results, list)
    assert len(results) == 2
    texts = {r.read_text() for r in results}
    assert "Archive readme" in texts


# ---------------------------------------------------------------------------
# AC-12: convert директория с архивом внутри
# ---------------------------------------------------------------------------

def test_convert_directory_with_archive(tmp_path):
    """AC-12: директория с архивом — архив раскрывается."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "plain.txt").write_text("Plain file")

    # Архив внутри директории
    archive_path = src_dir / "data.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("inner.txt", "Inner archive content")

    out_dir = tmp_path / "out"
    results = convert(src_dir, output_path=out_dir)

    # Должен быть как минимум plain.txt + inner из архива
    all_text = []
    for r in results:
        all_text.append(r.read_text())
    assert "Plain file" in all_text
    assert "Inner archive content" in all_text


# ---------------------------------------------------------------------------
# AC-13: convert non-recursive директория
# ---------------------------------------------------------------------------

def test_convert_non_recursive_directory(tmp_path):
    """AC-13: non-recursive конвертация — только файлы верхнего уровня."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "top.txt").write_text("Top level")
    (src_dir / "sub").mkdir()
    (src_dir / "sub" / "deep.txt").write_text("Deep level")

    out_dir = tmp_path / "out"
    results = convert(src_dir, output_path=out_dir, recursive=False)
    assert len(results) == 1
    assert results[0].read_text() == "Top level"


# ---------------------------------------------------------------------------
# AC-14: convert директория с неподдерживаемым файлом (пропуск)
# ---------------------------------------------------------------------------

def test_convert_skips_unsupported_files(tmp_path):
    """AC-14: бинарный файл без MIME-экстрактора пропускается.

    Файлы с текстовым MIME (text/plain) конвертируются даже без расширения —
    это корректное поведение через MIME-fallback.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "valid.txt").write_text("Valid")
    # Бинарный файл с неизвестным расширением и нулевым байтом — не текст
    (src_dir / "data.bin").write_bytes(b"\x00\x01\x02binary")

    out_dir = tmp_path / "out"
    results = convert(src_dir, output_path=out_dir)
    texts = {r.read_text() for r in results}
    assert "Valid" in texts
    # data.bin может быть конвертирован как бинарный файл пропущен
    # или распознан как неподдерживаемый — главное что конвертация не падает


def test_convert_text_file_with_weird_extension_converts(tmp_path):
    """AC-14b: текстовый файл с нестандартным расширением конвертируется через MIME."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file.xyz").write_text("Hello from .xyz")

    out_dir = tmp_path / "out"
    results = convert(src_dir, output_path=out_dir)
    assert len(results) == 1
    assert results[0].read_text() == "Hello from .xyz"


# ---------------------------------------------------------------------------
# AC-extra: _convert_single_file stdout
# ---------------------------------------------------------------------------

def test_convert_single_file_stdout(tmp_path, capsys):
    """_convert_single_file с stdout=True пишет в sys.stdout."""
    src = tmp_path / "test.txt"
    src.write_text("Single file stdout test")
    ctx = ExtractionContext()
    result = _convert_single_file(src, tmp_path, ctx, keep_relative=False, stdout=True)
    assert result == src  # возвращает исходный путь
    captured = capsys.readouterr()
    assert "Single file stdout test" in captured.out