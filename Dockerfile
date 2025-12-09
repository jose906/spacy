# Imagen base ligera y compatible con spaCy
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Dependencias mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download es_core_news_lg

COPY . .

# Cloud Run espera que el contenedor escuche en $PORT (default 8080)
ENV PORT=8080

EXPOSE 8080

# Usamos gunicorn leyendo PORT
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8080} main:app"]
