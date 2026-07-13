# any2md

Универсальный конвертер файлов в Markdown.

## Возможности

- Текстовые форматы: `txt`, `md`, `html`, `csv`, `json`, `xml`
- Офисные форматы: `docx`, `xlsx`, `pptx`
- PDF (с извлечением текста + OCR-фолбек)
- Изображения (OCR, опциональное описание)
- Архивы: `zip`, `tar`, `tar.gz`, `tar.bz2`, `tar.xz`
- Аудио/видео: `mp3`, `wav`, `mp4`, `mkv`, `webm` и др. через Whisper
- OpenDocument: `odt`, `ods`, `odp`
- Электронные книги: `fb2`, `epub`
- Пакетная обработка директорий в несколько потоков

## Установка

```bash
cd any2md
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OCR работает без системного Tesseract — any2md автоматически скачает bundled бинарник и языковые данные (eng, rus, fra, deu, spa) при первом использовании.

Если хотите использовать системный Tesseract, установите его вручную:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
```

## Использование

```bash
# Один файл
python -m any2md.cli document.docx -o output.md

# Директория рекурсивно
python -m any2md.cli ./docs -o ./docs_md --recursive --workers 8

# PDF/изображения с OCR
python -m any2md.cli scan.pdf -o scan.md --ocr --ocr-lang eng+rus

# Список поддерживаемых форматов
python -m any2md.cli --list-formats

# Вывод результата в stdout (pipe-friendly)
python -m any2md.cli scan.pdf -o -

# Аудио/видео с Whisper
python -m any2md.cli podcast.mp3 -o podcast.md --language ru
python -m any2md.cli lecture.mp4 -o lecture.md --whisper-model small --language en
```

### CLI-опция `--language`

- Для **Whisper** задаёт язык транскрибации (ISO-639-1, например `ru`, `en`, `de`).
- Если `--language` не указан, но включён `--ocr`, язык берётся из `--ocr-lang` (первая часть до `+`).
- Без `--language` Whisper автоматически определяет язык аудио.

## Графический интерфейс

```bash
# Запуск GUI
./any2md_gui.py

# Или через .desktop-файл (двойной клик)
./launch_any2md.desktop
```

Интерфейс позволяет:
- Выбрать входной **файл** или **папку**
- Указать выходной **файл** или **папку**
- Включить рекурсию, OCR, описание изображений
- Выбрать модель Whisper и язык
- Видеть лог процесса и открыть выходную папку

## Архитектура

```
any2md/
├── cli.py            # точка входа
├── core.py           # конвертация файлов/директорий
├── utils.py          # OCR, MIME, декодирование
└── extractors/
    ├── registry.py   # регистрация экстракторов
    ├── text.py       # txt/html/csv/json/xml
    ├── office.py     # docx/xlsx/pptx
    ├── pdf.py        # pdf
    ├── image.py      # изображения
    ├── archive.py    # архивы
    ├── media.py      # аудио/видео
    └── openoffice_ebook.py  # odt/ods/odp/fb2/epub
```

Новые форматы добавляются через декоратор `register_extractor` в `any2md/extractors/`.

---

## Поддержать разработку

Если any2md оказался полезным, можно поддержать автора:

- **USDT (TRC20):** `0x481E0A791dd9Dc0dBc9B20D81899E18786581442`
- **BTC:** `bc1q9st9f7mzwzqje7ku9mnervme5ed7z0ytkvp2p4`
- **ETH:** `0x481E0A791dd9Dc0dBc9B20D81899E18786581442`

**Версия:** 0.2.1
