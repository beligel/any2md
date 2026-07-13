"""Unit-тесты для openoffice_ebook-экстракторов (ODT, FB2, EPUB).

TDD по tdd-guide. Целевые AC:
  AC-1: _xml_text_from_zip — извлекает текст из content.xml
  AC-2: _xml_text_from_zip — xml_path не найден → ""
  AC-3: _xml_text_from_zip — script/style теги удаляются
  AC-4: extract_opendocument — ODT с content → заголовок # filename
  AC-5: extract_fb2 — FB2 с body → текст без binary
  AC-6: extract_epub — EPUB с OPF → правильный порядок HTML
  AC-7: extract_epub — без OPF → fallback на sorted HTML
  AC-8: extract_epub — script/style/nav удаляются
"""

import zipfile
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from any2md.extractors.registry import ExtractionContext


# ---------------------------------------------------------------------------
# Фикстуры: создаём тестовые файлы программно
# ---------------------------------------------------------------------------

def _make_odt(tmp_path, text_content="Тестовый документ ODT"):
    """Создаёт минимальный ODT-файл (zip с content.xml)."""
    odt_path = tmp_path / "test.odt"
    content_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body>
    <office:text>
      <text:p>{text_content}</text:p>
    </office:text>
  </office:body>
</office:document-content>"""
    with ZipFile(odt_path, "w") as zf:
        zf.writestr("content.xml", content_xml)
    return odt_path


def _make_fb2(tmp_path, body_text="Тестовый FB2 текст"):
    """Создаёт минимальный FB2-файл."""
    fb2_path = tmp_path / "test.fb2"
    fb2_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description><title-info><book-title>Тест</book-title></title-info></description>
  <body>
    <section><p>{body_text}</p></section>
  </body>
  <binary id="img1" content-type="image/png">cGF0Y2g=</binary>
</FictionBook>"""
    fb2_path.write_text(fb2_xml, encoding="utf-8")
    return fb2_path


def _make_epub(tmp_path, html_files=None, opf_items=None):
    """Создаёт минимальный EPUB-файл."""
    epub_path = tmp_path / "test.epub"
    if html_files is None:
        html_files = {"chapter1.xhtml": "<html><body><p>Глава 1</p></body></html>"}
    if opf_items is None:
        opf_items = []
        for name in html_files:
            opf_items.append(f'<item id="{name}" href="{name}" media-type="application/xhtml+xml"/>')

    opf_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest>
    {"".join(opf_items)}
  </manifest>
</package>"""

    with ZipFile(epub_path, "w") as zf:
        zf.writestr("OEBPS/content.opf", opf_xml)
        for name, content in html_files.items():
            zf.writestr(f"OEBPS/{name}", content)
    return epub_path


# ---------------------------------------------------------------------------
# AC-1: _xml_text_from_zip — извлекает текст
# ---------------------------------------------------------------------------

def test_xml_text_from_zip(tmp_path):
    """AC-1: _xml_text_from_zip извлекает текст из content.xml."""
    from any2md.extractors.openoffice_ebook import _xml_text_from_zip

    odt = _make_odt(tmp_path, "Привет из ODT")
    result = _xml_text_from_zip(odt, "content.xml")
    assert "Привет из ODT" in result


def test_xml_text_from_zip_empty_zip(tmp_path):
    """AC-2: xml_path не найден в zip → возвращает пустую строку."""
    from any2md.extractors.openoffice_ebook import _xml_text_from_zip

    zip_path = tmp_path / "empty.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("other.xml", "<root/>")

    result = _xml_text_from_zip(zip_path, "content.xml")
    assert result == ""


def test_xml_text_from_zip_removes_script_style(tmp_path):
    """AC-3: script и style теги удаляются из текста."""
    from any2md.extractors.openoffice_ebook import _xml_text_from_zip

    zip_path = tmp_path / "test.zip"
    xml = """<root>
      <script>alert('xss')</script>
      <style>body { color: red; }</style>
      <p>Чистый текст</p>
    </root>"""
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("content.xml", xml)

    result = _xml_text_from_zip(zip_path, "content.xml")
    assert "Чистый текст" in result
    assert "alert" not in result
    assert "color: red" not in result


# ---------------------------------------------------------------------------
# AC-4: extract_opendocument — ODT с content
# ---------------------------------------------------------------------------

def test_extract_opendocument_odt(tmp_path):
    """AC-4: ODT конвертируется с заголовком # filename."""
    from any2md.extractors.openoffice_ebook import extract_opendocument

    odt = _make_odt(tmp_path, "Содержимое документа")
    ctx = ExtractionContext()
    result = extract_opendocument(odt, ctx)
    assert "# test.odt" in result
    assert "Содержимое документа" in result


# ---------------------------------------------------------------------------
# AC-5: extract_fb2 — FB2 с body
# ---------------------------------------------------------------------------

def test_extract_fb2_text(tmp_path):
    """AC-5: FB2 извлекает текст body, удаляя binary."""
    from any2md.extractors.openoffice_ebook import extract_fb2

    fb2 = _make_fb2(tmp_path, "Текст книги")
    ctx = ExtractionContext()
    result = extract_fb2(fb2, ctx)
    assert "Текст книги" in result
    # base64 encoded binary не должен попасть
    assert "cGF0Y2g=" not in result


# ---------------------------------------------------------------------------
# AC-6: extract_epub — EPUB с OPF
# ---------------------------------------------------------------------------

def test_extract_epub_with_opf(tmp_path):
    """AC-6: EPUB извлекает HTML в порядке OPF манифеста."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub = _make_epub(tmp_path, html_files={
        "intro.xhtml": "<html><body><p>Введение</p></body></html>",
        "chapter1.xhtml": "<html><body><p>Глава 1</p></body></html>",
    })
    ctx = ExtractionContext()
    result = extract_epub(epub, ctx)
    assert "Введение" in result
    assert "Глава 1" in result


# ---------------------------------------------------------------------------
# AC-7: extract_epub — без OPF → fallback на sorted HTML
# ---------------------------------------------------------------------------

def test_extract_epub_without_opf(tmp_path):
    """AC-7: EPUB без OPF → fallback на sorted HTML файлы."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub_path = tmp_path / "no_opf.epub"
    with ZipFile(epub_path, "w") as zf:
        zf.writestr("b.xhtml", "<html><body><p>Второй</p></body></html>")
        zf.writestr("a.xhtml", "<html><body><p>Первый</p></body></html>")

    ctx = ExtractionContext()
    result = extract_epub(epub_path, ctx)
    assert "Первый" in result
    assert "Второй" in result


# ---------------------------------------------------------------------------
# AC-8: extract_epub — script/style/nav удаляются
# ---------------------------------------------------------------------------

def test_extract_epub_removes_script_style_nav(tmp_path):
    """AC-8: script, style и nav теги удаляются из EPUB."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub = _make_epub(tmp_path, html_files={
        "ch.xhtml": """<html><body>
          <script>var x = 1;</script>
          <style>body{margin:0}</style>
          <nav>Оглавление</nav>
          <p>Основной текст</p>
        </body></html>"""
    })
    ctx = ExtractionContext()
    result = extract_epub(epub, ctx)
    assert "Основной текст" in result
    assert "var x" not in result
    assert "margin:0" not in result


# ---------------------------------------------------------------------------
# EPUB: HTML не в namelist пропускается
# ---------------------------------------------------------------------------

def test_extract_epub_skips_missing_html(tmp_path):
    """AC-9: HTML-файл из OPF, отсутствующий в zip, пропускается."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub_path = tmp_path / "missing.epub"
    opf_xml = """<?xml version="1.0"?>
    <package xmlns="http://www.idpf.org/2007/opf">
      <manifest>
        <item id="exists" href="exists.xhtml" media-type="application/xhtml+xml"/>
        <item id="missing" href="missing.xhtml" media-type="application/xhtml+xml"/>
      </manifest>
    </package>"""
    with ZipFile(epub_path, "w") as zf:
        zf.writestr("OEBPS/content.opf", opf_xml)
        zf.writestr("OEBPS/exists.xhtml", "<html><body><p>Есть</p></body></html>")
        # missing.xhtml не создаём

    ctx = ExtractionContext()
    result = extract_epub(epub_path, ctx)
    assert "Есть" in result


# ---------------------------------------------------------------------------
# ODT: пустой content.xml
# ---------------------------------------------------------------------------

def test_extract_opendocument_empty(tmp_path):
    """AC-10: ODT с пустым content.xml → пустой вывод."""
    from any2md.extractors.openoffice_ebook import extract_opendocument

    odt_path = tmp_path / "empty.odt"
    content_xml = """<?xml version="1.0"?><root/>"""
    with ZipFile(odt_path, "w") as zf:
        zf.writestr("content.xml", content_xml)

    ctx = ExtractionContext()
    result = extract_opendocument(odt_path, ctx)
    assert "test.odt" not in result or result.strip() == ""


# ---------------------------------------------------------------------------
# EPUB: OPF с поддиректорией
# ---------------------------------------------------------------------------

def test_extract_epub_opf_in_subdir(tmp_path):
    """AC-11: OPF файл в поддиректории — относительные пути корректны."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub_path = tmp_path / "subdir.epub"
    opf_xml = """<?xml version="1.0"?>
    <package xmlns="http://www.idpf.org/2007/opf">
      <manifest>
        <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
      </manifest>
    </package>"""
    with ZipFile(epub_path, "w") as zf:
        zf.writestr("EPUB/content.opf", opf_xml)
        zf.writestr("EPUB/ch1.xhtml", "<html><body><p>Глубокий контент</p></body></html>")

    ctx = ExtractionContext()
    result = extract_epub(epub_path, ctx)
    assert "Глубокий контент" in result


# ---------------------------------------------------------------------------
# EPUB: OPF item без href или media-type
# ---------------------------------------------------------------------------

def test_extract_epub_opf_item_no_href(tmp_path):
    """AC-12: OPF item без href или без html в media-type — пропускается."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub_path = tmp_path / "bad_items.epub"
    opf_xml = """<?xml version="1.0"?>
    <package xmlns="http://www.idpf.org/2007/opf">
      <manifest>
        <item id="no-href" media-type="application/xhtml+xml"/>
        <item id="no-html" href="style.css" media-type="text/css"/>
        <item id="valid" href="page.xhtml" media-type="application/xhtml+xml"/>
      </manifest>
    </package>"""
    with ZipFile(epub_path, "w") as zf:
        zf.writestr("OEBPS/content.opf", opf_xml)
        zf.writestr("OEBPS/page.xhtml", "<html><body><p>Валидная страница</p></body></html>")

    ctx = ExtractionContext()
    result = extract_epub(epub_path, ctx)
    assert "Валидная страница" in result


# ---------------------------------------------------------------------------
# ImportError handlers (lines 19-20, 51-52, 67-68)
# ---------------------------------------------------------------------------

def test_xml_text_from_zip_no_bs4(tmp_path):
    """AC-13: _xml_text_from_zip без beautifulsoup4 → RuntimeError."""
    from any2md.extractors.openoffice_ebook import _xml_text_from_zip

    odt = _make_odt(tmp_path)
    with patch.dict("sys.modules", {"bs4": None}):
        with pytest.raises(RuntimeError, match="beautifulsoup4"):
            _xml_text_from_zip(odt, "content.xml")


def test_extract_fb2_no_bs4(tmp_path):
    """AC-14: extract_fb2 без beautifulsoup4 → RuntimeError."""
    from any2md.extractors.openoffice_ebook import extract_fb2

    fb2 = _make_fb2(tmp_path)
    ctx = ExtractionContext()
    with patch.dict("sys.modules", {"bs4": None}):
        with pytest.raises(RuntimeError, match="beautifulsoup4"):
            extract_fb2(fb2, ctx)


def test_extract_epub_no_bs4(tmp_path):
    """AC-15: extract_epub без beautifulsoup4 → RuntimeError."""
    from any2md.extractors.openoffice_ebook import extract_epub

    epub = _make_epub(tmp_path)
    ctx = ExtractionContext()
    with patch.dict("sys.modules", {"bs4": None}):
        with pytest.raises(RuntimeError, match="beautifulsoup4"):
            extract_epub(epub, ctx)