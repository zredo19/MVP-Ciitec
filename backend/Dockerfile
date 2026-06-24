FROM python:3.12-slim

# Dependencias de sistema para WeasyPrint (PDF), parsers y matplotlib.
# antiword: extrae texto de .doc binario (Word 97-2003) que python-docx no lee (RF-001).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
        libffi-dev libcairo2 libpangoft2-1.0-0 \
        libjpeg62-turbo zlib1g \
        fonts-dejavu-core \
        antiword \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
