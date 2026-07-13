"""Unit-тесты для text-экстракторов (txt, md, html, csv, json, xml).

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: .txt → содержимое как есть
  AC-2: .md → содержимое как есть
  AC-3: .html с <title> → «# Title» + body
  AC-4: .html без <title> → только body
  AC-5: .csv → markdown-таблица с разделителем
  AC-6: .csv пустой → пустая строка
  AC-7: .json → блок ```json с отступами
  AC-8: .xml → текст без тегов
  AC-9: .txt с не-UTF8 кодировкой → корректный декод
  AC-10: _fallback_text → оборачивает в код-блок
"""

from pathlib import Path

import pytest

from any2md.extractors.text import (
    _fallback_text,
    extract_csv,
    extract_html,
    extract_json,
    extract_md,
    extract_txt,
    extract_xml,
)
from any2md.extractors.registry import ExtractionContext


# ---------------------------------------------------------------------------
# AC-1: .txt → содержимое как есть
# ---------------------------------------------------------------------------

def test_txt_returns_content(tmp_path):
    """AC-1: .txt возвращает содержимое без изменений."""
    src = tmp_path / "test.txt"
    src.write_text("Hello world\nSecond line", encoding="utf-8")

    ctx = ExtractionContext()
    result = extract_txt(src, ctx)
    assert result == "Hello world\nSecond line"


# ---------------------------------------------------------------------------
# AC-2: .md → содержимое как есть
# ---------------------------------------------------------------------------

def test_md_returns_content(tmp_path):
    """AC-2: .md возвращает содержимое без изменений."""
    src = tmp_path / "test.md"
    src.write_text("# Header\n\nSome **markdown**", encoding="utf-8")

    ctx = ExtractionContext()
    result = extract_md(src, ctx)
    assert result == "# Header\n\nSome **markdown**"


# ---------------------------------------------------------------------------
# AC-3: .html с <title> → «# Title» + body
# ---------------------------------------------------------------------------

def test_html_with_title(tmp_path):
    """AC-3: HTML с <title> → заголовок первого уровня + тело."""
    src = tmp_path / "test.html"
    src.write_text(
        "<html><head><title>My Page</title></head>"
        "<body><p>Hello <b>world</b></p></body></html>",
        encoding="utf-8",
    )

    ctx = ExtractionContext()
    result = extract_html(src, ctx)
    assert "# My Page" in result
    assert "Hello" in result
    assert "world" in result


# ---------------------------------------------------------------------------
# AC-4: .html без <title> → только body
# ---------------------------------------------------------------------------

def test_html_without_title(tmp_path):
    """AC-4: HTML без <title> → только тело, без заголовка."""
    src = tmp_path / "test.html"
    src.write_text(
        "<html><body><p>No title here</p></body></html>",
        encoding="utf-8",
    )

    ctx = ExtractionContext()
    result = extract_html(src, ctx)
    assert "No title here" in result
    # Не должно быть пустого заголовка «# »
    assert not result.startswith("# \n\n")


# ---------------------------------------------------------------------------
# AC-5: .csv → markdown-таблица с разделителем
# ---------------------------------------------------------------------------

def test_csv_markdown_table(tmp_path):
    """AC-5: CSV конвертируется в markdown-таблицу."""
    src = tmp_path / "test.csv"
    src.write_text("Name,Age\nAlice,30\nBob,25", encoding="utf-8")

    ctx = ExtractionContext()
    result = extract_csv(src, ctx)
    assert "| Name | Age |" in result
    assert "| Alice | 30 |" in result
    assert "| Bob | 25 |" in result
    # Разделитель
    assert "---" in result


# ---------------------------------------------------------------------------
# AC-6: .csv пустой → пустая строка
# ---------------------------------------------------------------------------

def test_empty_csv_returns_empty_string(tmp_path):
    """AC-6: пустой CSV возвращает пустую строку."""
    src = tmp_path / "empty.csv"
    src.write_text("", encoding="utf-8")

    ctx = ExtractionContext()
    result = extract_csv(src, ctx)
    assert result == ""


# ---------------------------------------------------------------------------
# AC-7: .json → блок ```json с отступами
# ---------------------------------------------------------------------------

def test_json_code_block(tmp_path):
    """AC-7: JSON оборачивается в блок ```json с отступами."""
    src = tmp_path / "test.json"
    src.write_text('{"name":"тест","value":42}', encoding="utf-8")

    ctx = ExtractionContext()
    result = extract_json(src, ctx)
    assert result.startswith("```json\n")
    assert result.endswith("\n```")
    assert '"name": "тест"' in result  # ensure_ascii=False
    assert '"value": 42' in result
    # Отступы (indent=2)
    assert '\n  ' in result


# ---------------------------------------------------------------------------
# AC-8: .xml → текст без тегов
# ---------------------------------------------------------------------------

def test_xml_strips_tags(tmp_path):
    """AC-8: XML возвращает текст без тегов."""
    src = tmp_path / "test.xml"
    src.write_text(
        "<?xml version='1.0'?><root><item>Text content</item></root>",
        encoding="utf-8",
    )

    ctx = ExtractionContext()
    result = extract_xml(src, ctx)
    assert "Text content" in result
    assert "<root>" not in result
    assert "<item>" not in result


# ---------------------------------------------------------------------------
# AC-9: .txt с не-UTF8 кодировкой → корректный декод
# ---------------------------------------------------------------------------

def test_txt_windows1251(tmp_path):
    """AC-9: файл в windows-1251 декодируется корректно."""
    src = tmp_path / "test.txt"
    src.write_bytes("Привет мир".encode("windows-1251"))

    ctx = ExtractionContext(encoding="windows-1251")
    result = extract_txt(src, ctx)
    assert "Привет мир" in result


def test_txt_auto_decode_fallback(tmp_path):
    """AC-9b: maybe_decode fallback работает при неверной кодировке."""
    src = tmp_path / "test.txt"
    # Пишем в windows-1251, но просим utf-8 — должен сработать fallback
    src.write_bytes("Привет".encode("windows-1251"))

    ctx = ExtractionContext(encoding="utf-8")
    result = extract_txt(src, ctx)
    assert "Привет" in result  # maybe_decode пробует windows-1251 в fallback


# ---------------------------------------------------------------------------
# AC-10: _fallback_text → оборачивает в код-блок
# ---------------------------------------------------------------------------

def test_fallback_text_wraps_in_codeblock(tmp_path):
    """AC-10: _fallback_text оборачивает содержимое в код-блок."""
    src = tmp_path / "raw.txt"
    src.write_text("raw content", encoding="utf-8")

    ctx = ExtractionContext()
    result = _fallback_text(src, ctx)
    assert result.startswith("```\n")
    assert result.endswith("\n```")
    assert "raw content" in result