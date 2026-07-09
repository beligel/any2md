"""Базовые тесты any2md."""

import json
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
