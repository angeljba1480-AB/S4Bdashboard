# Guía: Conectar Ollama (ruta `local` privada) — MaestroAI

> **Objetivo:** que los datos **confidenciales** (ej. contrato BBVA con NDA) se
> procesen en **tu propia máquina** y **nunca salgan a la nube**. Lo no sensible
> sigue yendo a NaN (rápido); lo confidencial va a Ollama (privado).
>
> Esta guía es **modo prueba** desde tu **Mac** con un túnel temporal. Para
> producción, ver §6.

---

## 0. Cómo funciona (para que tengas el mapa mental)

```
Render (backend, en la nube)
   │  necesita una URL pública para hablarle a tu Ollama
   ▼
Cloudflare Tunnel  ──►  http://localhost:11434  (Ollama en TU Mac)
   (te da una URL https temporal)
```

Render no puede ver `localhost` de tu Mac. El **túnel** crea una URL pública
`https://algo.trycloudflare.com` que apunta a tu Ollama local. Así Render le
manda lo confidencial a tu máquina, y **el dato nunca sale de tu control**.

---

## 1. Instalar Ollama (en tu Mac)

Opción A — descarga la app: https://ollama.com/download
Opción B — con Homebrew:
```bash
brew install ollama
```

Arranca el servicio (deja esta terminal abierta, o la app corriendo):
```bash
ollama serve
```
> Si instalaste la app de macOS, ya corre sola en segundo plano. Puedes saltarte `ollama serve`.

---

## 2. Descargar un modelo

Para una prueba en Mac, un modelo pequeño/rápido:
```bash
ollama pull llama3.1        # 8B (~4.7 GB) — buen equilibrio
# alternativas más livianas/rápidas:
# ollama pull qwen2.5:3b    # ~1.9 GB, más rápido en CPU
# ollama pull llama3.2:3b   # ~2 GB
```

Pruébalo localmente (debe responder):
```bash
ollama run llama3.1 "Hola, responde en una línea."
```

> Recuerda el nombre exacto que descargaste (ej. `llama3.1` o `qwen2.5:3b`):
> ese será tu `LOCAL_MODEL`.

---

## 3. Exponer Ollama con Cloudflare Tunnel (gratis, sin cuenta)

Instala cloudflared:
```bash
brew install cloudflared
```

Levanta el túnel apuntando a Ollama (deja esta terminal abierta):
```bash
cloudflared tunnel --url http://localhost:11434
```

Verás algo como:
```
+----------------------------------------------------------+
|  https://random-words-1234.trycloudflare.com             |
+----------------------------------------------------------+
```
👉 **Copia esa URL.** Tu base para Render será esa URL **+ `/v1`**:
```
https://random-words-1234.trycloudflare.com/v1
```

Verifica que responde (en otra terminal):
```bash
curl https://random-words-1234.trycloudflare.com/v1/models
```
Debe listar tus modelos. ✅

---

## 4. Configurar Render

En **Render → servicio MaestroAI → Environment**, agrega/edita:

```
LOCAL_ENABLED        = true
LOCAL_BASE_URL       = https://random-words-1234.trycloudflare.com/v1
LOCAL_MODEL          = llama3.1          (el que descargaste)
ALLOW_CLOUD_FALLBACK = false             ← IMPORTANTE para blindar
```

> **¿Por qué `ALLOW_CLOUD_FALLBACK=false`?** Para que lo Confidencial/Restringido
> se quede SIEMPRE en Ollama. Si lo dejas en `true` y Ollama falla o tarda, el
> dato confidencial se "subiría" a NaN — justo lo que NO queremos.
>
> Con `false`: lo no sensible → NaN (rápido); lo confidencial → Ollama; si Ollama
> no está, lo confidencial cae al simulador (mock) en vez de salir a la nube. Seguro.

**Save, rebuild, and deploy** → espera "Live" (~2-3 min).

---

## 5. Probar 🎯

1. Portal → **Casos de uso → Propuesta comercial** (usa el contrato BBVA) → generar.
2. Debe decir **"por la ruta «local»"** y traer **contenido real** (no `mock-local`).
3. Ese texto lo generó **tu Mac** — el dato confidencial **nunca salió**. 🔒
4. **Descargar Word** para validar el entregable.

Para comprobar el contraste: un caso **sin** datos confidenciales debería seguir
saliendo por la ruta **«open»** (NaN). Así ves el enrutamiento por privacidad en vivo.

---

## 6. Producción (cuando dejes la prueba)

El túnel `trycloudflare` es **temporal**: la URL **cambia** cada vez que reinicias
`cloudflared`, y depende de que tu Mac esté encendida. Para algo estable:

- **Túnel con nombre (Cloudflare):** cuenta gratis + dominio → URL fija
  (`ollama.tudominio.com`). Docs: Cloudflare Zero Trust → Tunnels.
- **VM en la nube con GPU** (tu propia infra/VPC): instala Ollama ahí, ponle una
  URL pública con TLS, y usa esa en `LOCAL_BASE_URL`. Esto es lo correcto para
  volumen y disponibilidad 24/7.
- En ambos casos, considera proteger el endpoint (auth/IP allowlist) para que solo
  Render lo use.

---

## 7. Problemas comunes

| Síntoma | Causa / solución |
|---|---|
| Sigue saliendo `mock-local` | `LOCAL_ENABLED` no es `true`, o no se redesplegó, o la URL del túnel cambió. |
| Tarda mucho / timeout | Modelo grande en CPU. Usa uno más chico (`qwen2.5:3b`). El backend ya da 300s a la ruta local. |
| `connection refused` en el curl | Ollama no está corriendo (`ollama serve`) o el túnel se cerró. |
| La URL dejó de funcionar al día siguiente | `trycloudflare` es temporal: relanza el túnel y actualiza `LOCAL_BASE_URL` en Render. Para fijo, usa §6. |
| Caso confidencial cae a mock | Correcto si Ollama está caído y `ALLOW_CLOUD_FALLBACK=false`: el dato NO sale a la nube. Prende Ollama. |

---

## Resumen ultra-rápido (las 5 líneas)
```bash
brew install ollama cloudflared
ollama pull llama3.1
ollama serve                                   # (o la app de macOS)
cloudflared tunnel --url http://localhost:11434   # copia la URL
# En Render: LOCAL_ENABLED=true, LOCAL_BASE_URL=<url>/v1, LOCAL_MODEL=llama3.1, ALLOW_CLOUD_FALLBACK=false → Deploy
```

_MaestroAI · Guía de despliegue de la ruta privada (Ollama)._
