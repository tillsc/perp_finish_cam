#!/bin/bash

# Lokale Verzeichnisse
SRC_DIRS="data js"

# SSH-Zugangsdaten
REMOTE_USER="root"
REMOTE_HOST="perp.de"

# Zielbasisverzeichnis auf dem Remote-Host
REMOTE_BASE_DIR="/root/www/trsnet.de/httpdocs/perp_finish_cam_data"

# Lokale Informationen
LOCAL_HOSTNAME=$(hostname)
CURRENT_YEAR=$(date +"%Y")

# Zusammensetzen des Remote-Zielpfads
REMOTE_TARGET="${REMOTE_BASE_DIR}/${LOCAL_HOSTNAME}/${CURRENT_YEAR}"

# Erstellt das Zielverzeichnis auf dem Remote-Host, falls nicht vorhanden
ssh ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p '${REMOTE_TARGET}/data' '${REMOTE_TARGET}/js'"

# rsync-Befehl für jedes Quellverzeichnis
for DIR in $SRC_DIRS; do
  if [ -d "$DIR" ]; then
    echo "→ Synchronisiere '$DIR' nach ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_TARGET}/$DIR"
    rsync -avz --delete "$DIR/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_TARGET}/$DIR/"
  else
    echo "⚠️  Warnung: Verzeichnis '$DIR' existiert nicht und wird übersprungen."
  fi
done
