#!/usr/bin/env python3
"""CLI any2md."""

import argparse
import logging
import sys
from pathlib import Path

from .core import SUPPORTED_SUFFIXES, convert


def _print_supported_formats():
    print("Поддерживаемые форматы:")
    for suffix in sorted(set(SUPPORTED_SUFFIXES)):
        print(f"  {suffix}")


def main(argv=None):
    from any2md import __version__

    parser = argparse.ArgumentParser(
        prog="any2md",
        description="Конвертирует файлы (PDF, DOCX, TXT, HTML, изображения, аудио, видео и др.) в Markdown",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("input", nargs="?", help="Путь к входному файлу или директории")
    parser.add_argument("-o", "--output", help="Путь к выходному .md файлу или директории. Используйте '-' для stdout", default=None)
    parser.add_argument("--recursive", "-r", action="store_true", help="Обрабатывать директории рекурсивно")
    parser.add_argument("--ocr", action="store_true", help="Включить OCR для изображений/PDF")
    parser.add_argument("--ocr-lang", default="eng+rus", help="Языки для OCR (tesseract)")
    parser.add_argument("--image-desc", action="store_true", help="Генерировать описания изображений (базовые)")
    parser.add_argument("--encoding", default="utf-8", help="Кодировка текстовых файлов")
    parser.add_argument("--workers", type=int, default=4, help="Число параллельных воркеров")
    parser.add_argument("--whisper-model", default=None, help="Модель Whisper (tiny/base/small/medium/large)")
    parser.add_argument("--language", default=None, help="Язык для Whisper/OCR (ISO-639-1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument("--list-formats", action="store_true", help="Вывести список поддерживаемых форматов и выйти")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.list_formats:
        _print_supported_formats()
        raise SystemExit(0)

    if not args.input:
        parser.print_usage()
        print("Ошибка: укажите входной путь", file=sys.stderr)
        raise SystemExit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Ошибка: путь не найден: {input_path}", file=sys.stderr)
        return 1

    stdout = args.output == "-"

    try:
        language = args.language or (args.ocr_lang.split("+")[0] if args.ocr else None)
        result = convert(
            input_path,
            output_path=None if stdout else args.output,
            recursive=args.recursive,
            ocr=args.ocr,
            ocr_lang=args.ocr_lang,
            image_desc=args.image_desc,
            encoding=args.encoding,
            workers=args.workers,
            whisper_model=args.whisper_model,
            language=language,
            stdout=stdout,
        )
        if stdout:
            raise SystemExit(0)
        if isinstance(result, Path):
            print(result)
        else:
            for path in result:
                print(path)
        raise SystemExit(0)
    except Exception as exc:
        logging.error("Ошибка конвертации: %s", exc)
        if args.verbose:
            raise
        raise SystemExit(1)


if __name__ == "__main__":
    sys.exit(main())
