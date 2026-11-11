# ── Etapa única: imagen de producción ──────────────────────────────────────
FROM python:3.12-slim

# Evita que Python escriba .pyc y que bufferee stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Instala dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependencias Python primero (aprovecha caché de layers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente
COPY . .

# Expone el puerto de la API
EXPOSE 8000

# Script de entrada: aplica migraciones y lanza uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

