FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PROGRESS_BAR=off

WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copier uniquement les fichiers nécessaires à l'application
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Répertoire temporaire/local pour les uploads si nécessaire
RUN mkdir -p /app/uploads \
    && chown -R 10001:10001 /app

USER 10001:10001

# Railway fournit automatiquement PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
