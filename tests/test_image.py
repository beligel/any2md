"""Unit-тесты для image-экстрактора и extractors/__init__.

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: extract_image без OCR и без image_desc → markdown-ссылка
  AC-2: extract_image с image_desc → «*Изображение:*» + ссылка
  AC-3: extract_image с OCR → OCR текст
  AC-4: extract_image с OCR и пустым результатом → только ссылка
  AC-5: ExtractorRegistry.get возвращает None для неизвестного
  AC-6: get_extractor возвращает callable для .png
  AC-7: get_extractor возвращает None для неизвестного расширения
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from any2md.extractors.image import extract_image
from any2md.extractors.registry import ExtractionContext, get_extractor
from any2md.extractors import ExtractorRegistry


# ---------------------------------------------------------------------------
# AC-1: extract_image без OCR и без image_desc → markdown-ссылка
# ---------------------------------------------------------------------------

def test_image_default_markdown_link(tmp_path):
    """AC-1: без OCR и image_desc — markdown-ссылка ![name](name)."""
    src = tmp_path / "photo.png"
    src.write_bytes(b"fake png data")

    ctx = ExtractionContext()
    result = extract_image(src, ctx)
    assert "![photo.png](photo.png)" in result


# ---------------------------------------------------------------------------
# AC-2: extract_image с image_desc → «*Изображение:*» + ссылка
# ---------------------------------------------------------------------------

def test_image_with_description(tmp_path):
    """AC-2: image_desc=True → «*Изображение:*» в выводе."""
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"fake jpg data")

    ctx = ExtractionContext(image_desc=True)
    result = extract_image(src, ctx)
    assert "*Изображение:*" in result
    assert "photo.jpg" in result


# ---------------------------------------------------------------------------
# AC-3: extract_image с OCR → OCR текст
# ---------------------------------------------------------------------------

def test_image_with_ocr(tmp_path):
    """AC-3: ocr=True → OCR текст в выводе."""
    src = tmp_path / "scanned.png"
    src.write_bytes(b"fake png data")

    ctx = ExtractionContext(ocr=True)
    with patch("any2md.extractors.image.run_ocr", return_value="OCR recognized text"):
        result = extract_image(src, ctx)
    assert "OCR recognized text" in result


# ---------------------------------------------------------------------------
# AC-4: extract_image с OCR и пустым результатом → только ссылка
# ---------------------------------------------------------------------------

def test_image_ocr_empty_result_falls_back_to_link(tmp_path):
    """AC-4: OCR вернул пустоту → fallback на markdown-ссылку."""
    src = tmp_path / "blank.png"
    src.write_bytes(b"fake png data")

    ctx = ExtractionContext(ocr=True)
    with patch("any2md.extractors.image.run_ocr", return_value=""):
        result = extract_image(src, ctx)
    # Должна быть markdown-ссылка, т.к. OCR пустой
    assert "![blank.png](blank.png)" in result


# ---------------------------------------------------------------------------
# AC-5: ExtractorRegistry.get возвращает None для неизвестного
# ---------------------------------------------------------------------------

def test_extractor_registry_get_unknown_returns_none():
    """AC-5: ExtractorRegistry.get возвращает None для неизвестного расширения."""
    registry = ExtractorRegistry()
    result = registry.get(Path("test.unknownext123"))
    assert result is None


# ---------------------------------------------------------------------------
# AC-6: get_extractor возвращает callable для .png
# ---------------------------------------------------------------------------

def test_image_registered_for_png():
    """AC-6: get_extractor(Path('test.png')) возвращает callable.

    Реестр оборачивает функции в proxy, поэтому проверяем
    что возвращается callable."""
    result = get_extractor(Path("test.png"))
    assert result is not None
    assert callable(result)
    assert result.__name__ == "extract_image_proxy"


def test_image_registered_for_jpg():
    """AC-6b: get_extractor для .jpg возвращает callable."""
    result = get_extractor(Path("test.jpg"))
    assert result is not None


def test_image_registered_for_mime_wildcard():
    """AC-6c: get_extractor с MIME image/* находит экстрактор."""
    result = get_extractor(Path("test.unknown_img_ext"), mime="image/png")
    assert result is not None


# ---------------------------------------------------------------------------
# AC-7: get_extractor возвращает None для неизвестного расширения
# ---------------------------------------------------------------------------

def test_get_extractor_unknown_ext_no_mime_returns_none():
    """AC-7: get_extractor для неизвестного расширения без MIME → None."""
    result = get_extractor(Path("file.xyz123"))
    assert result is None