FROM python:3.12-slim

LABEL maintainer="MiMoCode User"

RUN apt-get update -qq && apt-get install -y -qq \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY any2md ./any2md
COPY any2md_gui.py ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

ENTRYPOINT ["any2md"]
CMD ["--help"]
