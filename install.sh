#!/usr/bin/env bash
# Установка any2md: создаёт venv, ставит зависимости, устанавливает desktop-запуск.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "== any2md installer =="

# Python
if ! command -v python3 &>/dev/null; then
    echo "Ошибка: python3 не найден. Установите Python 3.10+."
    exit 1
fi

PYVER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python: $PYVER"

# Системные зависимости
# Tesseract OCR больше не требуется — any2md скачает bundled бинарник при первом вызове OCR.
# Оставляем ffmpeg/libmagic1 как полезные системные пакеты.
if command -v apt-get &>/dev/null; then
    echo "Установка системных зависимостей (ffmpeg)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq ffmpeg libmagic1 || true
elif command -v dnf &>/dev/null; then
    sudo dnf install -y ffmpeg file-libs || true
elif command -v pacman &>/dev/null; then
    sudo pacman -Sy --noconfirm ffmpeg file || true
else
    echo "Предупреждение: не удалось автоматически установить ffmpeg. Установите вручную, если нужна обработка аудио/видео."
fi

# venv
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .

echo "== any2md установлен =="
echo "Запуск GUI:    ./any2md_gui.py"
echo "Запуск CLI:    any2md --help"

# Desktop-файл
if command -v xdg-desktop-menu &>/dev/null; then
    cp launch_any2md.desktop ~/.local/share/applications/any2md.desktop 2>/dev/null || true
    xdg-desktop-menu forceupdate 2>/dev/null || true
    echo "Ярлык добавлен в меню приложений."
fi
