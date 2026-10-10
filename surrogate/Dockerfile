# Image Python 3.13 (recommandé pour le développement web/backend) 
# Version slim (plus légère que la full debian avec compatibilité de bibliothèques + outils réseaux contrairement à alpine)
FROM python:3.13-slim AS surrogate

LABEL code="CDN"
LABEL version="v1"

# Installation des utilitaires réseau courants (--no-install-recommends pour garder une image légère)
# DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iperf3 \
    iproute2 \
    iputils-ping \
    netcat-openbsd \
    procps \
    tcpdump \
    traceroute \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail dans le conteneur
WORKDIR /code

# Copie des dépendances (pour le cache Docker)
COPY /code/requirements.txt /code

# Mise à jour de pip et installation de toutes les dépendances
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie des fichiers de l'codelication dans le conteneur
COPY /code /code

# Expose un port (pas obligatoire, seulement à titre indicatif)
EXPOSE 8080

# Démarre l'codelication au lancement du conteneur
CMD ["python", "main.py"]
