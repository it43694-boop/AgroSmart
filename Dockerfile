# ==========================================
# Dockerfile de Production pour AgroSmart
# Système Agricole Intelligent pour le Mali
# ==========================================

# Stage 1: Builder - Installation des dépendances
FROM python:3.10-slim AS builder

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd --create-home --shell /bin/bash agro

# Créer le répertoire de l'application
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Runtime - Image finale optimisée
# ==========================================

FROM python:3.10-slim AS runtime

# Installer les dépendances runtime minimales
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer un utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash --uid 1001 agro

# Créer les répertoires nécessaires
WORKDIR /app
RUN mkdir -p /app/data /app/logs && \
    chown -R agro:agro /app

# Copier les dépendances installées depuis le builder
COPY --from=builder --chown=agro:agro /root/.local /home/agro/.local
ENV PATH="/home/agro/.local/bin:$PATH"

# Copier le code de l'application
COPY --chown=agro:agro . .

# Variables d'environnement pour la production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    DATABASE_URL=sqlite:///data/agro_smart.db \
    PORT=8000

# Créer le volume pour la persistance des données
VOLUME ["/app/data", "/app/logs"]

# Exposer le port
# Expose a default port (Render will provide the actual $PORT at runtime)
EXPOSE 8000

# Changer vers l'utilisateur non-root
USER agro

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# Commande de démarrage optimisée pour la production
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --loop uvloop --http httptools --access-log --log-level info"