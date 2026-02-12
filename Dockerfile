FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Installer uv (gestionnaire de paquets du sujet)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copier le code
COPY . /app

# Installer les dépendances (d’après pyproject.toml)
RUN uv sync --frozen

# Port utilisé par Cloud Run
ENV PORT=8000

# Commande de démarrage : API FastAPI
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]