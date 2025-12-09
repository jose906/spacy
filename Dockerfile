# Imagen base ligera y compatible con spaCy
FROM python:3.10-slim

# Evitar interrupciones
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias para spaCy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libblas-dev \
    liblapack-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar paquetes Python
RUN pip install --no-cache-dir -r requirements.txt

# Descargar el modelo grande de spaCy
RUN python -m spacy download es_core_news_lg

# Copiar tu aplicación
COPY . .

CMD ["python", "main.py"]
