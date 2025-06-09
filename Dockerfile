FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir python-multipart

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]
