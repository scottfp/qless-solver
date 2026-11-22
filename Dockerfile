FROM python:3.12-slim

WORKDIR /app
COPY . .

# Note: OCR system packages (tesseract-ocr, libgl1, libglib2.0-0) and .[ocr]
# can be restored once computer vision letter detection is implemented.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]
