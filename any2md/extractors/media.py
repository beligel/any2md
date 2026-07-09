"""Экстрактор для аудио и видео через OpenAI Whisper."""

import logging
from pathlib import Path

from .registry import ExtractionContext, register_extractor

logger = logging.getLogger(__name__)

_AUDIO_VIDEO_EXTENSIONS = (
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma",
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
)


def _transcribe(path: Path, ctx: ExtractionContext) -> str:
    try:
        import whisper
    except ImportError:
        raise RuntimeError("Для аудио/видео нужно установить openai-whisper")

    return _do_whisper_transcribe(path, ctx, whisper)


def _do_whisper_transcribe(path: Path, ctx: ExtractionContext, whisper_module) -> str:
    model_name = ctx.whisper_model or "base"
    logger.info("Загрузка Whisper модели '%s'...", model_name)
    model = whisper_module.load_model(model_name)

    kwargs = {}
    if ctx.language:
        kwargs["language"] = ctx.language
        logger.info("Распознавание языка: %s", ctx.language)

    logger.info("Транскрибация %s...", path)
    result = model.transcribe(str(path), **kwargs)
    return result.get("text", "").strip()


@register_extractor("audio/*")
@register_extractor("video/*")
@register_extractor(".mp3")
@register_extractor(".wav")
@register_extractor(".flac")
@register_extractor(".aac")
@register_extractor(".ogg")
@register_extractor(".m4a")
@register_extractor(".wma")
@register_extractor(".mp4")
@register_extractor(".mkv")
@register_extractor(".avi")
@register_extractor(".mov")
@register_extractor(".wmv")
@register_extractor(".flv")
@register_extractor(".webm")
@register_extractor(".m4v")
def extract_media(path: Path, ctx: ExtractionContext, whisper_module=None) -> str:
    if whisper_module is None:
        text = _transcribe(path, ctx)
    else:
        text = _do_whisper_transcribe(path, ctx, whisper_module)
    return f"# Транскрибация: {path.name}\n\n{text}" if text else f"*Аудио/видео файл без распознанной речи:* `{path.name}`"
