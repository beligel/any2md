#!/usr/bin/env bash
# Графический лаунчер any2md — выбор файла/папки через Zenity
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if ! command -v zenity &>/dev/null; then
    echo "Zenity не найдена. Установите: sudo apt install zenity"
    read -r -p "Нажмите Enter..."
    exit 1
fi

MODE=$(zenity --list --title="any2md" --text="Что конвертировать?" \
    --column="Режим" "Файл" "Папку")

if [ -z "$MODE" ]; then
    exit 0
fi

if [ "$MODE" = "Файл" ]; then
    INPUT=$(zenity --file-selection --title="Выберите файл")
else
    INPUT=$(zenity --file-selection --directory --title="Выберите папку")
fi

if [ -z "$INPUT" ]; then
    exit 0
fi

OUTPUT=$(zenity --file-selection --save --title="Сохранить Markdown как" --filename="output.md")
if [ -z "$OUTPUT" ]; then
    exit 0
fi

OPTIONS=""
zenity --question --title="any2md" --text="Использовать OCR для изображений/PDF?" && OPTIONS="$OPTIONS --ocr" || true
zenity --question --title="any2md" --text="Обработать папку рекурсивно?" && OPTIONS="$OPTIONS --recursive" || true

LANGUAGE=$(zenity --entry --title="Язык" --text="Язык для Whisper/OCR (ru/en/de или пусто):" --entry-text="")
[ -n "$LANGUAGE" ] && OPTIONS="$OPTIONS --language $LANGUAGE"

MODEL=$(zenity --list --title="Модель Whisper" --text="Выберите модель (или tiny по умолчанию):" \
    --column="Модель" "tiny" "base" "small" "medium" "large")
[ -n "$MODEL" ] && OPTIONS="$OPTIONS --whisper-model $MODEL"

zenity --info --title="any2md" --text="Запуск конвертации..."

"$VENV_PYTHON" -m any2md.cli "$INPUT" -o "$OUTPUT" $OPTIONS --verbose

read -r -p "Готово. Нажмите Enter..."
