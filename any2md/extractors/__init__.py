"""Плагины-экстракторы для различных форматов файлов."""

from .registry import register_extractor, get_extractor

__all__ = ["ExtractorRegistry", "register_extractor", "get_extractor"]


class ExtractorRegistry:
    """Legacy compatibility wrapper around module-level registry."""

    def __init__(self):
        self._extractors = {}

    def register(self, key, extractor):
        from .registry import register_extractor

        register_extractor(key, extractor)
        self._extractors[key.lower()] = extractor

    def get(self, path, mime=None):
        from .registry import get_extractor

        return get_extractor(path, mime)
