# Configuración de tu parte — MaestroAI (paso a paso)

> Todo lo que **tú** configuras para que la plataforma deje el modo demostración y use
> tus modelos, tus cuentas y tus sistemas. El orden es de mayor a menor impacto.
> Atajo: entra a **Admin → Autochequeo del sistema** — te marca en verde/ámbar qué falta
> y trae la guía de cada hueco. Última actualización: 2026-06-27.

---

## 0. Dónde se configura cada cosa
- **Variables de entorno (backend Render)**: claves y flags globales del tenant.
- **Admin → Modelos y conectores**: proveedores de IA (NaN, premium, on-prem) con
  *Probar conexión*.
- **Integraciones**: correo, n8n, Zapier, SFTP, conectores de datos.
- **Mi cuenta**: MFA (tu verificación en dos pasos).

---

## 1. NaN Builders (el modelo) — **lo primero**
Sin esto el chat corre en modo demostración (mock).

1. Consigue tu **API key** de NaN (tier **inference** si quieres imágenes/voz; las
   *community* no generan imágenes).
2. **Admin → Modelos y conectores → Abierto (NaN)**:
   - Base URL: `https://api.nan.builders/v1`
   - Modelo: `qwen3.6`
   - API key: tu key
   - **Probar conexión** → debe responder ok + latencia.
3. (Opcional) Variables en Render para que también lo tomen procesos de fondo:
   ```
   OPEN_ENABLED=true
   OPEN_BASE_URL=https://api.nan.builders/v1
   OPEN_API_KEY=sk-tu-key
   OPEN_MODEL=qwen3.6
   ```

### 1a. Embeddings con NaN (mejor RAG)
Por defecto el RAG usa un embebedor local (baja calidad). Para usar NaN:
```
EMBEDDINGS_PROVIDER=open
EMBEDDINGS_MODEL=qwen3-embedding
EMBEDDINGS_DIM=4096
```
Luego **Documentos → Re-indexar RAG** (reconstruye los vectores con la nueva dimensión).

### 1b. Imágenes y voz (NaN)
- **Imágenes** (`flux-2-klein`) y **voz** (TTS `kokoro` / STT `whisper`) requieren key de
  **tier inference**. Con una key *community* devuelven error de permiso.
- No requieren configuración extra si el proveedor *Abierto* ya está puesto.

---

## 2. Modelo Premium (opcional — escalada de la cascada)
Para que la cascada pueda escalar a un modelo externo de máxima precisión. Sin esto,
todo corre en NaN (está bien).
- **Admin → Modelos y conectores → Premium**: Base URL + modelo + API key → *Probar conexión*.

---

## 3. Toolkit de acciones (Google / Microsoft) — para que el **agente ejecute**
NaN le da el "cerebro" al agente; esto le da las "manos".
1. **Integraciones → Conectar Google** y/o **Microsoft 365** (OAuth).
2. Para **escribir** (enviar correo, crear eventos/Docs, subir a Drive/OneDrive) otorga
   los **scopes de escritura** y reconecta — ver `ACCIONES-ESCRITURA-SETUP.md`.
3. En **Acciones** verás el catálogo; el agente usa solo lo que esté conectado.

---

## 4. n8n (automatizaciones / workflows)
1. Despliega **n8n** (self-hosted) y exponlo por HTTPS/túnel.
2. **Integraciones → n8n**: pega la Base URL del webhook + token, o configura
   `N8N_WEBHOOK_BASE_URL` (+ `N8N_ENABLED=true`) en Render.
3. Importa los flujos base de `integrations/n8n/` si los usas.
4. **Recetas a la medida**: *Integraciones → Recetas de automatización* (provider **n8n**).

---

## 5. Zapier (8,000+ apps)
- **Webhooks (listo ya)**: crea un Zap con trigger **Catch Hook**, copia la URL y créala
  en *Integraciones → Recetas de automatización* (provider **Zapier**). El agente la usa.
- **AI Actions (NLA)** *(opcional, nativo)*: requiere registro de app + API key en Zapier;
  luego `ZAPIER_NLA_ENABLED=true` y `ZAPIER_NLA_API_KEY=...`.

---

## 6. SFTP (sistemas legados con archivos)
- **Integraciones → Conector SFTP**: host, usuario, **contraseña o llave PEM**, ruta
  (archivo o carpeta) → *Probar* → *Importar* (trae PDF/DOCX/CSV/TXT al RAG).

---

## 7. Fine-tuning (LoRA) — entrenar en TU infra
NaN **no entrena**; el entrenamiento corre en tu hardware. Dos perfiles:
- **Mac / Apple Silicon (MLX)**: `integrations/n8n/` (`train-lora.sh` + `fuse-lora.sh`).
- **GPU NVIDIA (CUDA)**: `integrations/trainer-cuda/` (`train-lora-cuda.py`).

Variables en Render:
```
FINETUNE_ENABLED=true
FINETUNE_TRAINER_URL=https://<tu-n8n>/webhook/lora-train
FINETUNE_TRAINER_KEY=<token opcional>
FINETUNE_DEFAULT_BASE_MODEL=llama3.2:3b
```
Necesitas un **túnel** (Cloudflare/ngrok) para que el cloud alcance tu n8n/GPU y el
Ollama servido. Lanza los jobs desde *Fine-tuning*.

---

## 8. Seguridad
- **MFA**: *Mi cuenta → activar MFA (TOTP)*, escanea el QR y guarda los códigos de respaldo.
- **Cifrado en reposo**: define `MASTER_KMS_KEY` (32+ caracteres) en Render (en vez de
  reutilizar `SECRET_KEY`).
- **Antivirus**: `ANTIVIRUS_ENABLED=true` (+ `CLAMAV_HOST/PORT` opcional).

---

## 9. Despliegue
- **Render** (API) debe desplegar desde `main`. **Vercel** (portal) también desde `main`.
- Cada push a `main` dispara ambos despliegues.

---

## Resumen de variables (Render)
```
# Modelo abierto (NaN)
OPEN_ENABLED=true
OPEN_BASE_URL=https://api.nan.builders/v1
OPEN_API_KEY=sk-...
OPEN_MODEL=qwen3.6
# Embeddings con NaN (requiere re-indexar)
EMBEDDINGS_PROVIDER=open
EMBEDDINGS_MODEL=qwen3-embedding
EMBEDDINGS_DIM=4096
# Voz / imágenes usan OPEN_* (key tier inference)
# n8n
N8N_ENABLED=true
N8N_WEBHOOK_BASE_URL=https://<tu-n8n>/webhook
# Fine-tuning (opcional)
FINETUNE_ENABLED=true
FINETUNE_TRAINER_URL=https://<tu-n8n>/webhook/lora-train
# Zapier AI Actions (opcional)
ZAPIER_NLA_ENABLED=false
ZAPIER_NLA_API_KEY=
# Seguridad
MASTER_KMS_KEY=<32+ chars>
ANTIVIRUS_ENABLED=true
```

> Tras cambiar variables en Render, espera el redeploy y vuelve a correr el
> **Autochequeo** en *Admin* para confirmar que todo quedó en verde.
