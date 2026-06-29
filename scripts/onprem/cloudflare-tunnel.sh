#!/usr/bin/env bash
# MaestroAI · Túnel on-prem (Cloudflare) para exponer el lab local a la plataforma.
#
# Deja "construido" el camino on-prem: cuando quieras procesar lo CONFIDENCIAL en tu
# propia infra (no en NaN), corre este script en tu Mac/servidor del lab. Expone Ollama
# con una URL HTTPS pública; pegas esa URL en MaestroAI → Admin → Modelos → Local.
#
# Por ahora la operación va a NaN (sin retención, según su doc). Esto es para el día que
# se quiera fijar lo restringido a on-prem — sin reescribir nada.
#
# Uso:   bash scripts/onprem/cloudflare-tunnel.sh
# Requisitos: ollama, cloudflared  (macOS: brew install ollama cloudflared)
set -euo pipefail

CHAT_MODEL="${CHAT_MODEL:-llama3.2:3b}"      # alterna: deepseek-r1:8b
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

command -v ollama >/dev/null || { echo "Falta 'ollama' (brew install ollama)"; exit 1; }
command -v cloudflared >/dev/null || { echo "Falta 'cloudflared' (brew install cloudflared)"; exit 1; }

echo "▶ Asegurando Ollama y modelos…"
curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1 || { echo "  Inicia Ollama: 'ollama serve' en otra terminal"; exit 1; }
ollama pull "${CHAT_MODEL}"
ollama pull "${EMBED_MODEL}"   # para EMBEDDINGS_PROVIDER=local (embeddings privados)

cat <<EOF

▶ Abriendo túnel Cloudflare a ${OLLAMA_URL}
  Copia la URL https://<algo>.trycloudflare.com que aparezca y luego:

  1) MaestroAI → Admin → Modelos y conectores → Local (Ollama):
       Base URL : https://<tu-túnel>/v1
       Modelo   : ${CHAT_MODEL}
       Activo ✅ → Guardar → Probar conexión
  2) (Opcional, embeddings privados) en Render/API:
       EMBEDDINGS_PROVIDER=local
       EMBEDDINGS_MODEL=${EMBED_MODEL}
       EMBEDDINGS_DIM=768        # nomic-embed-text = 768
     y luego Documentos → Re-indexar RAG.

  El túnel quick (trycloudflare) da una URL nueva cada vez. Para una URL ESTABLE usa un
  named tunnel: 'cloudflared tunnel create maestro-ollama' + DNS a tu dominio.

EOF

exec cloudflared tunnel --url "${OLLAMA_URL}"
