"""any2md — универсальный конвертер файлов в Markdown."""

__version__ = "0.2.0"
__all__ = ["convert"]

# Автоматически импортируем все модули экстракторов, чтобы декораторы @register_extractor сработали.
import importlib
import pkgutil

import any2md.extractors  # noqa: F401

for _module_info in pkgutil.iter_modules(any2md.extractors.__path__):
    if _module_info.name.startswith("_"):
        continue
    try:
        importlib.import_module(f"any2md.extractors.{_module_info.name}")
    except Exception:
        pass
