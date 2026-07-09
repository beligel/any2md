#!/usr/bin/env python3
"""Графическое приложение any2md на tkinter + ttkbootstrap."""

import logging
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from any2md import __version__
from any2md.core import convert


HELP_TEXT = """any2md — Руководство пользователя

Версия: {version}

Что такое any2md
any2md — универсальный конвертер файлов и папок в Markdown.

Как запустить
- GUI: двойной клик по launch_any2md.desktop или ./any2md_gui.py
- CLI: python -m any2md.cli <input> -o <output>

Поддерживаемые форматы
- Текст: txt, md, html, htm, csv, json, xml
- Office: docx, xlsx, pptx
- PDF: pdf
- Изображения: png, jpg, jpeg, gif, bmp, tiff, webp
- Архивы: zip, tar, tar.gz, tar.bz2, tar.xz
- Аудио/видео: mp3, wav, mp4, mkv, webm и др. (через Whisper)
- OpenDocument: odt, ods, odp
- Электронные книги: fb2, epub

Основные опции CLI
  -o, --output        Путь для сохранения
  --recursive         Рекурсивная обработка папки
  --ocr               Включить OCR
  --ocr-lang          Язык(и) OCR (например, eng+rus)
  --image-desc        Описание изображений
  --language          Язык для Whisper/OCR (ru, en, de...)
  --whisper-model     Модель Whisper (tiny/base/small/medium/large)
  --encoding          Кодировка текстовых файлов
  --workers           Число параллельных воркеров
  --verbose           Подробный вывод

Требования
- Python 3.10+
- Установленные зависимости из requirements.txt
- Tesseract OCR загружается автоматически при первом использовании (английский, русский, французский, немецкий, испанский)
- Для аудио/видео: ffmpeg

Поддержать разработку
Если any2md оказался полезным, можно поддержать автора:
- USDT (TRC20): 0x481E0A791dd9Dc0dBc9B20D81899E18786581442
- BTC: bc1q9st9f7mzwzqje7ku9mnervme5ed7z0ytkvp2p4
- ETH: 0x481E0A791dd9Dc0dBc9B20D81899E18786581442
"""


class Any2MdApp:
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title(f"any2md {__version__} — Конвертер в Markdown")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)

        self.style = ttk.Style("litera")

        self.input_path = ttk.StringVar()
        self.output_path = ttk.StringVar()
        self.recursive = ttk.BooleanVar(value=True)
        self.ocr = ttk.BooleanVar(value=False)
        self.ocr_lang = ttk.StringVar(value="eng+rus")
        self.image_desc = ttk.BooleanVar(value=False)
        self.whisper_model = ttk.StringVar(value="base")
        self.language = ttk.StringVar(value="")
        self.encoding = ttk.StringVar(value="utf-8")
        self.workers = ttk.IntVar(value=4)

        self._build_ui()
        self._setup_logging()

    def _build_ui(self):
        # Заголовок
        header = ttk.Label(
            self.root,
            text="any2md — универсальный конвертер файлов в Markdown",
            font=("Helvetica", 16, "bold"),
        )
        header.pack(pady=(20, 10))

        # Основной контейнер
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # --- Вход ---
        in_frame = ttk.LabelFrame(main_frame, text="Вход")
        in_frame.pack(fill=X, pady=5)
        in_inner = ttk.Frame(in_frame, padding=10)
        in_inner.pack(fill=X)

        ttk.Entry(in_inner, textvariable=self.input_path).pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        ttk.Button(in_inner, text="Файл", command=self._choose_file, bootstyle=SECONDARY).pack(side=LEFT, padx=2)
        ttk.Button(in_inner, text="Папка", command=self._choose_dir, bootstyle=SECONDARY).pack(side=LEFT, padx=2)

        # --- Выход ---
        out_frame = ttk.LabelFrame(main_frame, text="Выход")
        out_frame.pack(fill=X, pady=5)
        out_inner = ttk.Frame(out_frame, padding=10)
        out_inner.pack(fill=X)

        ttk.Entry(out_inner, textvariable=self.output_path).pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        ttk.Button(out_inner, text="Сохранить как...", command=self._choose_output, bootstyle=SECONDARY).pack(side=LEFT, padx=2)

        # --- Опции ---
        options_frame = ttk.LabelFrame(main_frame, text="Опции конвертации")
        options_frame.pack(fill=X, pady=5)
        opts_inner = ttk.Frame(options_frame, padding=10)
        opts_inner.pack(fill=X)

        # Левая колонка
        left_col = ttk.Frame(opts_inner)
        left_col.pack(side=LEFT, fill=Y, expand=YES, anchor=N)

        ttk.Checkbutton(left_col, text="Рекурсивно обрабатывать папку", variable=self.recursive).pack(anchor=W, pady=2)
        ttk.Checkbutton(left_col, text="OCR для изображений/PDF", variable=self.ocr).pack(anchor=W, pady=2)
        ttk.Checkbutton(left_col, text="Описание изображений", variable=self.image_desc).pack(anchor=W, pady=2)

        # Правая колонка
        right_col = ttk.Frame(opts_inner)
        right_col.pack(side=LEFT, fill=Y, expand=YES, anchor=N)

        ttk.Label(right_col, text="Язык OCR/Whisper (ISO-639-1):").pack(anchor=W)
        ttk.Entry(right_col, textvariable=self.ocr_lang, width=15).pack(anchor=W, pady=2)

        ttk.Label(right_col, text="Модель Whisper:").pack(anchor=W)
        whisper_combo = ttk.Combobox(
            right_col,
            textvariable=self.whisper_model,
            values=["tiny", "base", "small", "medium", "large"],
            state="readonly",
            width=15,
        )
        whisper_combo.pack(anchor=W, pady=2)

        ttk.Label(right_col, text="Кодировка текстовых файлов:").pack(anchor=W)
        ttk.Entry(right_col, textvariable=self.encoding, width=15).pack(anchor=W, pady=2)

        ttk.Label(right_col, text="Параллельных воркеров:").pack(anchor=W)
        ttk.Spinbox(right_col, from_=1, to=16, textvariable=self.workers, width=15).pack(anchor=W, pady=2)

        # --- Кнопки ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=15)

        self.run_btn = ttk.Button(
            btn_frame,
            text="▶ Запустить конвертацию",
            command=self._run_conversion,
            bootstyle=SUCCESS,
        )
        self.run_btn.pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Открыть выходную папку",
            command=self._open_output_dir,
            bootstyle=INFO,
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Сбросить",
            command=self._reset,
            bootstyle=WARNING,
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Помощь",
            command=self._show_help,
            bootstyle=LIGHT,
        ).pack(side=LEFT, padx=5)

        # --- Лог ---
        log_frame = ttk.LabelFrame(main_frame, text="Лог")
        log_frame.pack(fill=BOTH, expand=YES)
        log_inner = ttk.Frame(log_frame, padding=10)
        log_inner.pack(fill=BOTH, expand=YES)

        self.log_text = ttk.Text(log_inner, height=10, wrap="word", state="disabled")
        self.log_text.pack(fill=BOTH, expand=YES)

        # Прогресс
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate", bootstyle=INFO)
        self.progress.pack(fill=X, pady=(10, 0))

        # Статус
        self.status = ttk.Label(main_frame, text="Готово", anchor=W)
        self.status.pack(fill=X, pady=(5, 0))

    def _setup_logging(self):
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def _choose_file(self):
        path = filedialog.askopenfilename(title="Выберите файл для конвертации")
        if path:
            self.input_path.set(path)
            self._guess_output(Path(path))

    def _choose_dir(self):
        path = filedialog.askdirectory(title="Выберите папку для конвертации")
        if path:
            self.input_path.set(path)
            self._guess_output(Path(path), is_dir=True)

    def _choose_output(self):
        input_p = Path(self.input_path.get()) if self.input_path.get() else None
        if input_p and input_p.is_dir():
            path = filedialog.askdirectory(title="Выберите выходную папку")
        else:
            path = filedialog.asksaveasfilename(
                title="Сохранить Markdown как",
                defaultextension=".md",
                filetypes=[("Markdown", "*.md"), ("Все файлы", "*.*")],
            )
        if path:
            self.output_path.set(path)

    def _guess_output(self, path: Path, is_dir: bool = False):
        if is_dir or path.is_dir():
            self.output_path.set(str(path.parent / (path.name + "_md")))
        else:
            self.output_path.set(str(path.with_suffix(".md")))

    def _open_output_dir(self):
        out = self.output_path.get()
        if not out:
            messagebox.showwarning("Внимание", "Сначала укажите выходной путь")
            return
        out_path = Path(out)
        target = out_path if out_path.is_dir() else out_path.parent
        if target.exists():
            import subprocess
            subprocess.Popen(["xdg-open", str(target)])
        else:
            messagebox.showwarning("Внимание", f"Папка не существует: {target}")

    def _reset(self):
        self.input_path.set("")
        self.output_path.set("")
        self.recursive.set(True)
        self.ocr.set(False)
        self.ocr_lang.set("eng+rus")
        self.image_desc.set(False)
        self.whisper_model.set("base")
        self.language.set("")
        self.encoding.set("utf-8")
        self.workers.set(4)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.status.configure(text="Готово")

    def _show_help(self):
        help_win = ttk.Toplevel(self.root)
        help_win.title(f"Помощь — any2md {__version__}")
        help_win.geometry("650x550")
        help_win.transient(self.root)
        help_win.grab_set()

        text = ttk.Text(help_win, wrap="word", state="normal", padx=10, pady=10)
        text.pack(fill=BOTH, expand=YES)
        text.insert("1.0", HELP_TEXT.format(version=__version__))
        text.configure(state="disabled")

        vsb = ttk.Scrollbar(help_win, orient="vertical", command=text.yview)
        vsb.pack(side="right", fill="y")
        text.configure(yscrollcommand=vsb.set)

        ttk.Button(help_win, text="Закрыть", command=help_win.destroy, bootstyle=SECONDARY).pack(pady=10)

    def _run_conversion(self):
        input_path = self.input_path.get()
        output_path = self.output_path.get()

        if not input_path or not Path(input_path).exists():
            messagebox.showerror("Ошибка", "Укажите существующий входной файл или папку")
            return
        if not output_path:
            messagebox.showerror("Ошибка", "Укажите выходной путь")
            return

        language = self.ocr_lang.get().split("+")[0] if not self.language.get() else self.language.get()

        self.run_btn.configure(state="disabled", text="Конвертация...")
        self.progress.start()
        self.status.configure(text="Конвертация запущена...")

        def worker():
            try:
                result = convert(
                    input_path,
                    output_path=output_path,
                    recursive=self.recursive.get(),
                    ocr=self.ocr.get(),
                    ocr_lang=self.ocr_lang.get(),
                    image_desc=self.image_desc.get(),
                    encoding=self.encoding.get(),
                    workers=self.workers.get(),
                    whisper_model=self.whisper_model.get(),
                    language=language,
                )
                self.root.after(0, lambda: self._on_done(result))
            except Exception as exc:
                logging.exception("Ошибка конвертации")
                self.root.after(0, lambda: self._on_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, result):
        self.progress.stop()
        self.run_btn.configure(state="normal", text="▶ Запустить конвертацию")
        self.status.configure(text="Готово")
        if isinstance(result, Path):
            messagebox.showinfo("Готово", f"Сохранено:\n{result}")
        else:
            messagebox.showinfo("Готово", f"Сконвертировано файлов: {len(result)}")

    def _on_error(self, exc):
        self.progress.stop()
        self.run_btn.configure(state="normal", text="▶ Запустить конвертацию")
        self.status.configure(text="Ошибка")
        messagebox.showerror("Ошибка", str(exc))


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + "\n"
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", msg)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")


def main():
    root = ttk.Window(themename="litera")
    app = Any2MdApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
