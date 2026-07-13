"""Unit-тесты для any2md.utils.

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: maybe_decode — UTF-8 по умолчанию
  AC-2: maybe_decode — fallback на windows-1251
  AC-3: maybe_decode — fallback на latin-1 (всегда работает)
  AC-4: get_mime_type — возвращает MIME для файла
  AC-5: get_mime_type — пустая строка при ошибке
  AC-6: is_binary — True для бинарного файла
  AC-7: is_binary — False для текстового файла
  AC-8: ensure_dir — создаёт вложенные папки
  AC-9: run_ocr — пустая строка при отсутствии pytesseract
  AC-10: run_ocr — пустая строка при ошибке OCR
  AC-11: configure_tesseract — не падает при отсутствии bundled
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from any2md.utils import (
    configure_tesseract,
    ensure_dir,
    get_mime_type,
    is_binary,
    maybe_decode,
    run_ocr,
)


# ---------------------------------------------------------------------------
# AC-1: maybe_decode — UTF-8 по умолчанию
# ---------------------------------------------------------------------------

def test_maybe_decode_utf8(tmp_path):
    """AC-1: maybe_decode читает UTF-8."""
    src = tmp_path / "test.txt"
    src.write_text("Hello мир", encoding="utf-8")
    assert maybe_decode(src) == "Hello мир"


# ---------------------------------------------------------------------------
# AC-2: maybe_decode — fallback на windows-1251
# ---------------------------------------------------------------------------

def test_maybe_decode_windows1251_fallback(tmp_path):
    """AC-2: maybe_decode fallback на windows-1251."""
    src = tmp_path / "test.txt"
    src.write_bytes("Привет".encode("windows-1251"))
    # Просим неизвестную кодировку — fallback дойдёт до windows-1251
    result = maybe_decode(src, encoding="ascii")
    assert "Привет" in result


# ---------------------------------------------------------------------------
# AC-3: maybe_decode — fallback на latin-1 (всегда работает)
# ---------------------------------------------------------------------------

def test_maybe_decode_latin1_always_succeeds(tmp_path):
    """AC-3: latin-1 декодирует любые байты без ошибки."""
    src = tmp_path / "test.bin"
    src.write_bytes(b"\xff\xfe\xfd\xfc")
    result = maybe_decode(src, encoding="utf-8")
    # Не должно бросать — latin-1 последняя попытка
    assert isinstance(result, str)
    assert len(result) == 4


# ---------------------------------------------------------------------------
# AC-4: get_mime_type — возвращает MIME для файла
# ---------------------------------------------------------------------------

def test_get_mime_type_returns_mime(tmp_path):
    """AC-4: get_mime_type возвращает MIME-тип."""
    src = tmp_path / "test.txt"
    src.write_text("hello", encoding="utf-8")
    mime = get_mime_type(src)
    # python-magic может вернуть text/plain или пустую строку если не установлен
    assert mime == "" or "text" in mime


# ---------------------------------------------------------------------------
# AC-5: get_mime_type — пустая строка при ошибке
# ---------------------------------------------------------------------------

def test_get_mime_type_empty_on_error(tmp_path):
    """AC-5: get_mime_type возвращает '' для несуществующего файла."""
    result = get_mime_type(tmp_path / "nonexistent")
    assert result == ""


# ---------------------------------------------------------------------------
# AC-6: is_binary — True для бинарного файла
# ---------------------------------------------------------------------------

def test_is_binary_true(tmp_path):
    """AC-6: is_binary возвращает True для бинарного файла."""
    src = tmp_path / "test.bin"
    src.write_bytes(b"\x00\x01\x02\x03binary\xff")
    assert is_binary(src) is True


# ---------------------------------------------------------------------------
# AC-7: is_binary — False для текстового файла
# ---------------------------------------------------------------------------

def test_is_binary_false(tmp_path):
    """AC-7: is_binary возвращает False для текстового файла."""
    src = tmp_path / "test.txt"
    src.write_text("Hello world", encoding="utf-8")
    assert is_binary(src) is False


def test_is_binary_empty_file(tmp_path):
    """AC-7b: пустой файл — не бинарный (нет нулевых байтов)."""
    src = tmp_path / "empty.txt"
    src.write_bytes(b"")
    assert is_binary(src) is False


# ---------------------------------------------------------------------------
# AC-8: ensure_dir — создаёт вложенные папки
# ---------------------------------------------------------------------------

def test_ensure_dir_creates_nested(tmp_path):
    """AC-8: ensure_dir создаёт вложенные директории."""
    target = tmp_path / "a" / "b" / "c"
    result = ensure_dir(target)
    assert target.exists()
    assert target.is_dir()
    assert result == target


def test_ensure_dir_idempotent(tmp_path):
    """AC-8b: ensure_dir не падает при повторном вызове."""
    target = tmp_path / "existing"
    target.mkdir()
    result = ensure_dir(target)
    assert target.exists()
    assert result == target


# ---------------------------------------------------------------------------
# AC-9: run_ocr — пустая строка при отсутствии pytesseract
# ---------------------------------------------------------------------------

def test_run_ocr_returns_empty_without_pytesseract(tmp_path):
    """AC-9: run_ocr возвращает '' если pytesseract не установлен."""
    src = tmp_path / "fake.png"
    src.write_bytes(b"fake image")

    import sys
    # Временно скрываем pytesseract и PIL
    with patch.dict(sys.modules, {"pytesseract": None, "PIL": None, "PIL.Image": None}):
        result = run_ocr(src, "eng")
    assert result == ""


# ---------------------------------------------------------------------------
# AC-10: run_ocr — пустая строка при ошибке OCR
# ---------------------------------------------------------------------------

def test_run_ocr_returns_empty_on_exception(tmp_path):
    """AC-10: run_ocr возвращает '' при ошибке открытия изображения."""
    src = tmp_path / "fake.png"
    src.write_bytes(b"not a real image")

    # pytesseract и PIL доступны, но Image.open упадёт
    result = run_ocr(src, "eng")
    assert result == ""


# ---------------------------------------------------------------------------
# AC-11: configure_tesseract — не падает при отсутствии bundled
# ---------------------------------------------------------------------------

def test_configure_tesseract_does_not_raise(tmp_path, monkeypatch):
    """AC-11: configure_tesseract не падает, если bundled tesseract отсутствует."""
    # Меняем PATH чтобы системный tesseract не нашёлся
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setattr(
        "any2md.tesseract_bundled._base_dir",
        lambda: tmp_path / ".any2md" / "tesseract",
    )
    # Не должно бросать
    configure_tesseract()