#!/usr/bin/env bash
# Instalacion de las herramientas de Impacto en el VPS (Oracle Cloud
# Always Free, ARM Ampere A1, Ubuntu 22.04).
#
# Que hace:
#   1. Instala python3, pip y venv con apt.
#   2. Crea /opt/impacto-tools y copia aqui los archivos de tools/ si se
#      corre desde el repo (si ya estan, no hace nada).
#   3. Crea un entorno virtual en /opt/impacto-tools/venv e instala
#      requirements.txt dentro.
#   4. Verifica que RapidOCR se puede importar.
#
# Es idempotente: se puede correr dos veces sin romper nada.
# No pide ni guarda credenciales: el JSON de la cuenta de servicio se pone
# a mano despues, en /opt/impacto-tools/service-account.json (fuera del repo).
#
# Uso:
#   sudo bash install.sh            # desde la carpeta tools/ del repo
set -euo pipefail

DESTINO="/opt/impacto-tools"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "== 1/4 apt: python3, pip y venv =="
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv > /dev/null
echo "OK: $(python3 --version)"

echo "== 2/4 carpeta $DESTINO =="
mkdir -p "$DESTINO"
# Copiar los archivos de tools/ si este install.sh vive en el repo.
# Si ya estan en $DESTINO, la copia es la misma y no estropea nada.
for f in renombrar_fotos.py requirements.txt README.md; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$DESTINO/$f"
    fi
done
chmod +x "$DESTINO/renombrar_fotos.py" 2>/dev/null || true

echo "== 3/4 entorno virtual e instalacion de requirements =="
if [ ! -d "$DESTINO/venv" ]; then
    python3 -m venv "$DESTINO/venv"
fi
"$DESTINO/venv/bin/pip" install -q --upgrade pip
"$DESTINO/venv/bin/pip" install -q -r "$DESTINO/requirements.txt"

echo "== 4/4 verificacion de RapidOCR =="
"$DESTINO/venv/bin/python" -c "from rapidocr_onnxruntime import RapidOCR; print('OK: RapidOCR se importa bien')"

echo ""
echo "Instalado en $DESTINO"
echo "Siguiente paso: poner el JSON de la cuenta de servicio en"
echo "  $DESTINO/service-account.json"
echo "y probar en seco con:"
echo "  $DESTINO/venv/bin/python $DESTINO/renombrar_fotos.py --dry-run"
