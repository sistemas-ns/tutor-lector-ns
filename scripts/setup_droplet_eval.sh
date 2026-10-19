#!/usr/bin/env bash
# Prepara el droplet de evaluación del Tutor Lector NS.
# Ubuntu 24.04, 16 GB RAM. Ejecutar como root:  bash setup_droplet_eval.sh
# Si lo corres desde la consola web de DigitalOcean (sin SSH), pásale tu IP
# pública de casa/oficina como argumento:  bash setup_droplet_eval.sh 190.x.x.x
set -euo pipefail

echo "== 1/4 Instalando Ollama =="
curl -fsSL https://ollama.com/install.sh | sh

echo "== 2/4 Configurando el servicio (escuchar en red + modelo fijo en RAM) =="
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_KEEP_ALIVE=2h"
EOF
systemctl daemon-reload
systemctl restart ollama
sleep 5

echo "== 3/4 Cortafuegos: SSH abierto, Ollama SOLO para tu IP =="
MI_IP="${1:-}"
if [ -z "$MI_IP" ]; then
  MI_IP=$(echo "${SSH_CLIENT:-}" | awk '{print $1}')
fi
if [ -z "$MI_IP" ]; then
  echo "ERROR: no detecté tu IP. Vuelve a correr: bash setup_droplet_eval.sh TU_IP_PUBLICA"
  echo "(tu IP pública la ves en https://ifconfig.me desde tu navegador)"
  exit 1
fi
ufw default deny incoming
ufw allow OpenSSH
ufw allow from "$MI_IP" to any port 11434 proto tcp
ufw --force enable
echo "   Puerto 11434 autorizado únicamente para: $MI_IP"

echo "== 4/4 Descargando los modelos candidatos (~18 GB en total, toma un rato) =="
# Qwen3 8B: se intenta la variante instruct; si no existe en la librería,
# se usa la híbrida (el harness ya sabe apagarle el razonamiento con /no_think).
ollama pull qwen3:8b-instruct || ollama pull qwen3:8b
ollama pull llama3.1:8b
ollama pull gemma3:12b

echo ""
echo "================ LISTO ================"
ollama list
echo ""
free -h | head -2
echo ""
echo "Prueba rápida del servicio:"
curl -s http://localhost:11434/api/version
echo ""
echo "Siguiente paso: pasa a Claude la IP PUBLICA de este droplet para"
echo "correr el harness de evaluación desde la máquina de desarrollo."
