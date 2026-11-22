# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    QLESS_DICTIONARY_PATH=/app/dictionary.txt \
    QLESS_COMMON_DICTIONARY_PATH=/app/common_words.txt

WORKDIR /app

# Copy dictionaries separately so code-only rebuilds reuse this cached ~10 MB layer
COPY dictionary.txt common_words.txt ./

# Install package and runtime dependencies
COPY pyproject.toml README.md LICENSE ./
COPY cli/ ./cli/
RUN uv pip install --system --no-cache .

# Note: OCR system packages (tesseract-ocr, libgl1, libglib2.0-0) and .[ocr]
# can be restored once computer vision letter detection is implemented (Phase 4).
COPY web/ ./web/

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn web.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
