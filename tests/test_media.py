"""Unit-тесты для медиа-экстрактора any2md."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from any2md.extractors.media import _do_whisper_transcribe, extract_media
from any2md.extractors.registry import ExtractionContext


def test_extract_media_with_transcription(tmp_path):
    fake_path = tmp_path / "sample.mp3"
    fake_path.write_text("dummy")  # файл как placeholder

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "  Привет, мир!  "}

    fake_whisper = MagicMock()
    fake_whisper.load_model.return_value = fake_model

    ctx = ExtractionContext(whisper_model="tiny", language="ru")

    result = extract_media(fake_path, ctx, whisper_module=fake_whisper)
    assert "# Транскрибация: sample.mp3" in result
    assert "Привет, мир!" in result
    fake_whisper.load_model.assert_called_once_with("tiny")
    fake_model.transcribe.assert_called_once_with(str(fake_path), language="ru")


def test_extract_media_empty_transcription(tmp_path):
    fake_path = tmp_path / "silence.wav"
    fake_path.write_text("dummy")

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "   "}

    fake_whisper = MagicMock()
    fake_whisper.load_model.return_value = fake_model

    ctx = ExtractionContext()
    result = extract_media(fake_path, ctx, whisper_module=fake_whisper)
    assert "без распознанной речи" in result
    fake_whisper.load_model.assert_called_once_with("base")


def test_do_whisper_transcribe_no_language(tmp_path):
    fake_path = tmp_path / "auto.mp4"
    fake_path.write_text("dummy")

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "hello world"}

    fake_whisper = MagicMock()
    fake_whisper.load_model.return_value = fake_model

    ctx = ExtractionContext(whisper_model="base")
    result = _do_whisper_transcribe(fake_path, ctx, fake_whisper)
    assert result == "hello world"
    fake_model.transcribe.assert_called_once_with(str(fake_path))


def test_extract_media_registered_for_extensions():
    from any2md.extractors.registry import get_extractor

    for ext in [".mp3", ".wav", ".mp4", ".webm", ".ogg"]:
        assert get_extractor(Path(f"test{ext}")) is not None, f"no extractor for {ext}"


def test_extract_media_supported_by_core(tmp_path, monkeypatch):
    """Проверяем, что core корректно передаёт медиа-файл в экстрактор."""
    from any2md.extractors import media as media_module
    from any2md.extractors.registry import get_extractor

    fake_path = tmp_path / "podcast.mp3"
    fake_path.write_text("dummy")

    captured = {}

    def fake_extract_media(path: Path, ctx: ExtractionContext, whisper_module=None) -> str:
        captured["path"] = path
        captured["language"] = ctx.language
        captured["model"] = ctx.whisper_model
        return f"transcribed: {path.name}"

    # Мокаем непосредственно функцию, зарегистрированную в реестре
    monkeypatch.setattr(media_module, "extract_media", fake_extract_media)
    # Перерегистрируем замоканную функцию, чтобы core её нашёл
    from any2md.extractors.registry import _REGISTRY

    for key in list(_REGISTRY.keys()):
        if _REGISTRY[key].__name__ == "extract_media":
            _REGISTRY[key] = fake_extract_media

    from any2md import core

    result = core.convert(fake_path, whisper_model="tiny", language="ru")
    assert result.read_text() == "transcribed: podcast.mp3"
    assert captured["path"] == fake_path
    assert captured["language"] == "ru"
    assert captured["model"] == "tiny"
