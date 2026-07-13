"""Unit-тесты для any2md.tesseract_bundled.

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: _get_expected_sha256 — env-override работает
  AC-2: _get_expected_sha256 — None если нет ни env, ни константы
  AC-3: _sha256_file — корректный хэш
  AC-4: _is_executable — True для исполняемого, False для отсутствующего
  AC-5: _merge_tree — сливает деревья без удаления существующих
  AC-6: _find_libtesseract — находит .so файл
  AC-7: _find_libtesseract — None если нет .so
  AC-8: _base_dir / _tessdata_dir / _binary_path — корректные пути
  AC-9: cleanup_bundled_tesseract — удаляет директорию
  AC-10: get_tesseract_cmd — системный tesseract имеет приоритет
  AC-11: _download_with_fallback — бросает RuntimeError если все URL недоступны
  AC-12: _download_with_fallback — проверяет SHA256
"""

import hashlib
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from any2md.tesseract_bundled import (
    LANGS,
    LEPTONICA_VERSION,
    PACKAGES,
    TESSERACT_VERSION,
    _base_dir,
    _binary_path,
    _download_with_fallback,
    _find_libtesseract,
    _get_expected_sha256,
    _is_executable,
    _merge_tree,
    _sha256_file,
    _tessdata_dir,
    cleanup_bundled_tesseract,
    get_tesseract_cmd,
)


# ---------------------------------------------------------------------------
# AC-1: _get_expected_sha256 — env-override работает
# ---------------------------------------------------------------------------

def test_get_expected_sha256_env_override(monkeypatch):
    """AC-1: env ANY2MD_SHA256_<PKG> перекрывает встроенную константу."""
    monkeypatch.setenv("ANY2MD_SHA256_LIBTESSERACT5", "abc123")
    result = _get_expected_sha256("libtesseract5")
    assert result == "abc123"


# ---------------------------------------------------------------------------
# AC-2: _get_expected_sha256 — None если нет ни env, ни константы
# ---------------------------------------------------------------------------

def test_get_expected_sha256_none_default(monkeypatch):
    """AC-2: _get_expected_sha256 возвращает None если SHA256 не задан."""
    monkeypatch.delenv("ANY2MD_SHA256_TESSERACT_OCR", raising=False)
    result = _get_expected_sha256("tesseract-ocr")
    assert result is None


# ---------------------------------------------------------------------------
# AC-3: _sha256_file — корректный хэш
# ---------------------------------------------------------------------------

def test_sha256_file(tmp_path):
    """AC-3: _sha256_file возвращает корректный SHA256 хэш."""
    src = tmp_path / "test.bin"
    data = b"hello world"
    src.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert _sha256_file(src) == expected


# ---------------------------------------------------------------------------
# AC-4: _is_executable — True для исполняемого, False для отсутствующего
# ---------------------------------------------------------------------------

def test_is_executable_true(tmp_path):
    """AC-4: _is_executable True для исполняемого файла."""
    src = tmp_path / "script.sh"
    src.write_text("#!/bin/bash\necho hello")
    src.chmod(src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    assert _is_executable(src) is True


def test_is_executable_false_nonexistent(tmp_path):
    """AC-4b: _is_executable False для несуществующего файла."""
    assert _is_executable(tmp_path / "nonexistent") is False


def test_is_executable_false_no_exec_bit(tmp_path):
    """AC-4c: _is_executable False для файла без execute-бита."""
    src = tmp_path / "file.txt"
    src.write_text("hello")
    src.chmod(0o644)  # rw-r--r-- — нет execute
    assert _is_executable(src) is False


# ---------------------------------------------------------------------------
# AC-5: _merge_tree — сливает деревья без удаления существующих
# ---------------------------------------------------------------------------

def test_merge_tree(tmp_path):
    """AC-5: _merge_tree сливает исходное дерево в целевое."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    # Создаём структуру в src
    (src / "dir1").mkdir(parents=True)
    (src / "dir1" / "file1.txt").write_text("content1")
    (src / "file2.txt").write_text("content2")

    # В dst уже есть dir1
    (dst / "dir1").mkdir(parents=True)
    (dst / "dir1" / "existing.txt").write_text("old")

    _merge_tree(src, dst)

    assert (dst / "dir1" / "file1.txt").read_text() == "content1"
    assert (dst / "dir1" / "existing.txt").read_text() == "old"  # не удалён
    assert (dst / "file2.txt").read_text() == "content2"


# ---------------------------------------------------------------------------
# AC-6: _find_libtesseract — находит .so файл
# ---------------------------------------------------------------------------

def test_find_libtesseract_finds_so(tmp_path):
    """AC-6: _find_libtesseract находит libtesseract.so."""
    base = tmp_path / "base"
    lib_dir = base / "usr" / "lib" / "x86_64-linux-gnu"
    lib_dir.mkdir(parents=True)
    so_file = lib_dir / "libtesseract.so.5"
    so_file.write_text("fake lib")

    result = _find_libtesseract(base)
    assert result is not None
    assert result.name == "libtesseract.so.5"


# ---------------------------------------------------------------------------
# AC-7: _find_libtesseract — None если нет .so
# ---------------------------------------------------------------------------

def test_find_libtesseract_none(tmp_path):
    """AC-7: _find_libtesseract возвращает None если нет .so."""
    base = tmp_path / "empty"
    base.mkdir()
    result = _find_libtesseract(base)
    assert result is None


# ---------------------------------------------------------------------------
# AC-8: пути _base_dir / _tessdata_dir / _binary_path
# ---------------------------------------------------------------------------

def test_base_dir_contains_any2md():
    """AC-8: _base_dir содержит .any2md/tesseract в пути."""
    result = _base_dir()
    assert ".any2md" in str(result)
    assert "tesseract" in str(result)


def test_binary_path_under_base():
    """AC-8b: _binary_path указывает на usr/bin/tesseract."""
    result = _binary_path()
    assert "usr" in str(result)
    assert "bin" in str(result)
    assert "tesseract" in str(result)


# ---------------------------------------------------------------------------
# AC-9: cleanup_bundled_tesseract — удаляет директорию
# ---------------------------------------------------------------------------

def test_cleanup_removes_directory(tmp_path, monkeypatch):
    """AC-9: cleanup_bundled_tesseract удаляет папку .any2md/tesseract."""
    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_base.mkdir(parents=True)
    (fake_base / "some_file").write_text("data")

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    cleanup_bundled_tesseract()

    assert not fake_base.exists()


def test_cleanup_noop_if_not_exists(tmp_path, monkeypatch):
    """AC-9b: cleanup_bundled_tesseract не падает если папки нет."""
    monkeypatch.setattr(
        "any2md.tesseract_bundled._base_dir",
        lambda: tmp_path / ".any2md" / "nonexistent",
    )
    # Не должно бросать
    cleanup_bundled_tesseract()


# ---------------------------------------------------------------------------
# AC-10: get_tesseract_cmd — системный tesseract имеет приоритет
# ---------------------------------------------------------------------------

def test_get_tesseract_cmd_system_priority(monkeypatch):
    """AC-10: если системный tesseract есть, bundled не используется."""
    monkeypatch.setattr("any2md.tesseract_bundled.shutil.which", lambda _: "/usr/bin/tesseract")
    cmd, prefix = get_tesseract_cmd()
    assert cmd == "/usr/bin/tesseract"
    assert prefix == ""


def test_get_tesseract_cmd_returns_none_if_no_binary(monkeypatch, tmp_path):
    """AC-10b: get_tesseract_cmd возвращает None если бинарник не появился."""
    monkeypatch.setattr("any2md.tesseract_bundled.shutil.which", lambda _: None)
    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: tmp_path / "fake_base")
    monkeypatch.setattr(
        "any2md.tesseract_bundled._binary_path",
        lambda: tmp_path / "fake_base" / "usr" / "bin" / "tesseract",
    )
    # install_tesseract не должна сработать без сети — патчим
    monkeypatch.setattr(
        "any2md.tesseract_bundled.install_tesseract",
        lambda: None,
    )
    result = get_tesseract_cmd()
    assert result is None


# ---------------------------------------------------------------------------
# AC-11: _download_with_fallback — бросает RuntimeError если все URL недоступны
# ---------------------------------------------------------------------------

def test_download_with_fallback_raises_on_all_failures(tmp_path):
    """AC-11: _download_with_fallback бросает RuntimeError если все URL недоступны."""
    dest = tmp_path / "output.deb"

    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        with pytest.raises(RuntimeError, match="Не удалось скачать"):
            _download_with_fallback(["http://fake1/test.deb", "http://fake2/test.deb"], dest)


# ---------------------------------------------------------------------------
# AC-12: _download_with_fallback — проверяет SHA256
# ---------------------------------------------------------------------------

def test_download_with_fallback_sha256_mismatch(tmp_path):
    """AC-12: _download_with_fallback бросает RuntimeError при несовпадении SHA256.

    Функция ловит внутреннюю SHA256-ошибку и оборачивает в RuntimeError
    «Не удалось скачать», поэтому проверяем внешнее сообщение.
    """
    dest = tmp_path / "output.deb"
    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": "11"}
    fake_response.read = MagicMock(side_effect=[b"hello world", b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises(RuntimeError, match="Не удалось скачать"):
            _download_with_fallback(
                ["http://fake/test.deb"],
                dest,
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )
    # Файл должен быть удалён при ошибке
    assert not dest.exists()


def test_download_with_fallback_sha256_match(tmp_path):
    """AC-12b: _download_with_fallback проходит при совпадении SHA256."""
    dest = tmp_path / "output.deb"
    data = b"hello world"
    correct_sha = hashlib.sha256(data).hexdigest()

    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": str(len(data))}
    fake_response.read = MagicMock(side_effect=[data, b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_response):
        _download_with_fallback(
            ["http://fake/test.deb"],
            dest,
            expected_sha256=correct_sha,
        )

    assert dest.read_bytes() == data


# ---------------------------------------------------------------------------
# Константы версий (AC-extra: проверка что константы определены)
# ---------------------------------------------------------------------------

def test_version_constants_defined():
    """Константы версий определены и непусты."""
    assert TESSERACT_VERSION
    assert LEPTONICA_VERSION
    assert len(LANGS) == 5
    assert "eng" in LANGS
    assert "rus" in LANGS
    assert "libtesseract5" in PACKAGES
    assert "tesseract-ocr" in PACKAGES
    assert "liblept5" in PACKAGES