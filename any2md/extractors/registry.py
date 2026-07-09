"""Реестр экстракторов и dispatch-логика по MIME/ext."""

from pathlib import Path
from typing import Callable, Optional

Extractor = Callable[[Path, "ExtractionContext"], str]

_REGISTRY: dict[str, Extractor] = {}


class ExtractionContext:
    """Контекст извлечения для одного файла."""

    def __init__(self, ocr: bool = False, ocr_lang: str = "eng", image_desc: bool = False, encoding: str = "utf-8", whisper_model: str | None = None, language: str | None = None):
        self.ocr = ocr
        self.ocr_lang = ocr_lang
        self.image_desc = image_desc
        self.encoding = encoding
        self.whisper_model = whisper_model
        self.language = language


def register_extractor(mime_or_ext: str, extractor: Extractor | None = None) -> Extractor:
    """Регистрирует экстрактор для MIME-типа или расширения (с точкой).

    Поддерживает использование как декоратора: @register_extractor('.txt').
    В реестре сохраняется обёртка, которая динамически разрешает текущую
    функцию в модуле — это позволяет monkeypatch'ить экстракторы в тестах.
    """

    def _register(fn: Extractor) -> Extractor:
        key = mime_or_ext.lower()

        def _proxy(path: Path, ctx: ExtractionContext) -> str:
            import importlib
            mod = importlib.import_module(_proxy._target_module)
            real = getattr(mod, _proxy._target_name)
            return real(path, ctx)

        _proxy.__name__ = f"{fn.__name__}_proxy"
        _proxy._target_module = fn.__module__
        _proxy._target_name = fn.__name__
        _REGISTRY[key] = _proxy
        return fn

    if extractor is None:
        return _register
    return _register(extractor)


def get_extractor(path: Path, mime: Optional[str] = None) -> Optional[Extractor]:
    """Подбирает экстрактор по расширению, затем по MIME (wildcard)."""
    ext = path.suffix.lower()
    if ext in _REGISTRY:
        return _REGISTRY[ext]

    if mime:
        mime = mime.lower().split(";", 1)[0].strip()
        if mime in _REGISTRY:
            return _REGISTRY[mime]
        # wildcard, e.g. image/*
        category = mime.split("/", 1)[0] + "/*"
        if category in _REGISTRY:
            return _REGISTRY[category]

    return None
