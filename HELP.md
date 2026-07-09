# any2md — Руководство пользователя

**Версия:** 0.2.0

## Что такое any2md

`any2md` — это универсальный конвертер файлов и папок в Markdown. Поддерживает текстовые документы, офисные форматы, PDF, изображения, архивы, аудио и видео.

---

## Как запустить

### Вариант 1: Графический интерфейс (GUI)

Двойной клик по файлу `launch_any2md.desktop` или запуск в терминале:

```bash
cd /home/che/projects/any2md
./any2md_gui.py
```

### Вариант 2: Командная строка (CLI)

```bash
cd /home/che/projects/any2md
source .venv/bin/activate

# Один файл
python -m any2md.cli document.docx -o output.md

# Папка рекурсивно
python -m any2md.cli ./docs -o ./docs_md --recursive

# PDF или изображение с OCR
python -m any2md.cli scan.pdf -o scan.md --ocr --ocr-lang eng+rus

# Аудио/видео с Whisper
python -m any2md.cli podcast.mp3 -o podcast.md --language ru
```

---

## Поддерживаемые форматы

| Категория | Форматы |
|-----------|---------|
| Текст | `txt`, `md`, `html`, `htm`, `csv`, `json`, `xml` |
| Microsoft Office | `docx`, `xlsx`, `pptx` |
| PDF | `pdf` |
| Изображения | `png`, `jpg`, `jpeg`, `gif`, `bmp`, `tiff`, `webp` |
| Архивы | `zip`, `tar`, `tar.gz`, `tar.bz2`, `tar.xz` |
| Аудио | `mp3`, `wav`, `flac`, `aac`, `ogg`, `m4a`, `wma` |
| Видео | `mp4`, `mkv`, `avi`, `mov`, `wmv`, `flv`, `webm`, `m4v` |
| OpenDocument | `odt`, `ods`, `odp` |
| Электронные книги | `fb2`, `epub` |

---

## Графический интерфейс

1. **Вход** — нажмите «Файл» или «Папка» и выберите источник.
2. **Выход** — нажмите «Сохранить как...» и укажите, куда сохранить результат.
3. **Опции**:
   - **Рекурсивно обрабатывать папку** — обработать все файлы во вложенных папках.
   - **OCR для изображений/PDF** — распознавать текст на картинках и сканах.
   - **Описание изображений** — добавлять базовые подписи к картинкам.
   - **Язык OCR/Whisper** — язык распознавания (`ru`, `en`, `de` и др.).
   - **Модель Whisper** — размер модели для аудио/видео (`tiny`, `base`, `small`, `medium`, `large`).
   - **Кодировка** — кодировка текстовых файлов (обычно `utf-8`).
   - **Параллельных воркеров** — сколько файлов обрабатывать одновременно.
4. Нажмите **▶ Запустить конвертацию**.
5. В окне **Лог** отображается ход работы.
6. Кнопка **Открыть выходную папку** открывает результат в файловом менеджере.
7. Кнопка **Сбросить** очищает все поля.

---

## CLI: основные опции

| Опция | Описание | Пример |
|-------|----------|--------|
| `-o, --output` | Путь для сохранения | `-o result.md` |
| `--recursive` | Рекурсивная обработка папки | `--recursive` |
| `--ocr` | Включить OCR | `--ocr` |
| `--ocr-lang` | Язык(и) OCR | `--ocr-lang eng+rus` |
| `--image-desc` | Описание изображений | `--image-desc` |
| `--language` | Язык для Whisper/OCR | `--language ru` |
| `--whisper-model` | Модель Whisper | `--whisper-model small` |
| `--encoding` | Кодировка текста | `--encoding utf-8` |
| `--workers` | Число потоков | `--workers 8` |
| `--verbose` | Подробный вывод | `--verbose` |

---

## Требования

- Python 3.10+
- Установленные зависимости из `requirements.txt`
- Для OCR: системный пакет `tesseract-ocr`
- Для аудио/видео: `ffmpeg` (обычно уже установлен в Linux)

Установка зависимостей:

```bash
cd /home/che/projects/any2md
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Поддержать разработку

Если any2md оказался полезным, можно поддержать автора:

- **USDT (TRC20):** `0x481E0A791dd9Dc0dBc9B20D81899E18786581442`
- **BTC:** `bc1q9st9f7mzwzqje7ku9mnervme5ed7z0ytkvp2p4`
- **ETH:** `0x481E0A791dd9Dc0dBc9B20D81899E18786581442`

---

## Где находятся файлы

- Код приложения: `/home/che/projects/any2md/any2md/`
- GUI: `/home/che/projects/any2md/any2md_gui.py`
- Тесты: `/home/che/projects/any2md/tests/`
- Иконка: `/home/che/projects/any2md/icon.svg`
- Лаунчер: `/home/che/projects/any2md/launch_any2md.desktop`
