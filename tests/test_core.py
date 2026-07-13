"""Базовые тесты any2md."""

import json
import zipfile
from pathlib import Path

from any2md.core import convert


def test_txt(tmp_path):
    src = tmp_path / "hello.txt"
    src.write_text("Hello world")
    out = convert(src)
    assert out.read_text() == "Hello world"


def test_json(tmp_path):
    src = tmp_path / "data.json"
    src.write_text(json.dumps({"key": "value"}, ensure_ascii=False))
    out = convert(src)
    assert "value" in out.read_text()


def test_directory(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("A")
    (src_dir / "b.txt").write_text("B")
    results = convert(src_dir, output_path=tmp_path / "out")
    assert len(results) == 2
    texts = {r.read_text() for r in results}
    assert texts == {"A", "B"}


def test_explicit_output_file(tmp_path):
    src = tmp_path / "hello.txt"
    src.write_text("Hello")
    target = tmp_path / "custom.md"
    out = convert(src, output_path=target)
    assert out == target
    assert out.read_text() == "Hello"


def test_mime_fallback_for_extensionless(tmp_path):
    src = tmp_path / "readme"
    src.write_text("Extensionless text file")
    results = convert(tmp_path, output_path=tmp_path / "out")
    assert len(results) == 1
    assert results[0].read_text() == "Extensionless text file"


def test_archive_single_file_conversion(tmp_path):
    archive_dir = tmp_path / "archive_content"
    archive_dir.mkdir()
    (archive_dir / "inner.txt").write_text("Archive content")

    archive_path = tmp_path / "test.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(archive_dir / "inner.txt", "inner.txt")

    results = convert(archive_path, output_path=tmp_path / "out")
    assert len(results) == 1
    assert results[0].read_text() == "Archive content"


def test_progress_callback(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("A")
    (src_dir / "b.txt").write_text("B")

    events = []

    def cb(current, total):
        events.append((current, total))

    convert(src_dir, output_path=tmp_path / "out", progress_callback=cb)
    assert events
    assert events[-1][0] == events[-1][1]
