#!/bin/bash

# Lokale Verzeichnisse
SRC_DIRS="data js"

# Ziel-Host und -Basisverzeichnis
REMOTE_HOST="perp.de"
REMOTE_BASE_DIR="./www/trsnet.de/httpdocs/perp_finish_cam_data"

# Hostname der lokalen Maschine
LOCAL_HOSTNAME=$(hostname)

# Aktuelles Jahr
DATE_DIR=$(date +"%Y")

# Zielverzeichnis auf dem Remote-Host
REMOTE_DIR="${REMOTE_BASE_DIR}/${LOCAL_HOSTNAME}/${DATE_DIR}"

# rsync-Befehl mit --delete und -avz für Archivmodus, Kompression und ausführliche Ausgabe
for DIR in $SRC_DIRS; do
  if [ -d "$DIR" ]; then
    echo "Synchronisiere $DIR nach ${REMOTE_HOST}:${REMOTE_DIR}/$DIR"
    rsync -avz --delete "$DIR/" "${REMOTE_HOST}:${REMOTE_DIR}/$DIR/"
  else
    echo "Warnung: Verzeichnis '$DIR' existiert nicht und wird übersprungen."
  fi
done