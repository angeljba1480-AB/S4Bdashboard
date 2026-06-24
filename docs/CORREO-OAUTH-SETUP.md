# Guía: Conectar correo real (Outlook / Gmail) — MaestroAI

> Habilita el caso **«Resumen de correo y agenda»** para que lea la bandeja y el
> calendario **reales** del usuario. Tu correo es **hotmail.com**, así que tu
> proveedor es **Microsoft (Outlook)**. La guía incluye también Gmail.

Cómo funciona: el usuario entra a **Integraciones → Conectar correo**, autoriza
con Microsoft/Google (OAuth), y el token se guarda **cifrado**. Al correr el caso,
MaestroAI lee correo + agenda, los pasa por el **enrutador de privacidad** (PII
redactado) y genera el resumen.

---

## A) Microsoft / Outlook (lo que tú necesitas)

### 1. Registrar la app en Azure (Entra ID)
1. Entra a **https://portal.azure.com** → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Nombre: `MaestroAI`.
3. **Supported account types:** elige
   *“Accounts in any organizational directory and personal Microsoft accounts”*
   (esto cubre hotmail/outlook personales + empresas).
4. **Redirect URI:** tipo **Web** →
   `https://s4bdashboard.onrender.com/oauth/microsoft/callback`
   *(usa la URL real de tu backend en Render).*
5. **Register**.

### 2. Permisos (scopes)
1. **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated**.
2. Agrega: `User.Read`, `Mail.Read`, `Calendars.Read`, `offline_access`.
3. (Opcional) **Grant admin consent**.

### 3. Secreto
1. **Certificates & secrets** → **New client secret** → copia el **Value** (solo se ve una vez).
2. Copia también el **Application (client) ID** del Overview.

### 4. Variables en Render
```
MICROSOFT_OAUTH_ENABLED = true
MICROSOFT_CLIENT_ID     = <Application (client) ID>
MICROSOFT_CLIENT_SECRET = <el Value del secreto>
MICROSOFT_TENANT        = common
MICROSOFT_REDIRECT_URI  = https://s4bdashboard.onrender.com/oauth/microsoft/callback
APP_PUBLIC_URL          = https://plataforma.maestroai.mx
```
→ **Save, rebuild, and deploy**.

---

## B) Google / Gmail (opcional)

1. **https://console.cloud.google.com** → crea proyecto → **APIs & Services**.
2. Habilita **Gmail API** y **Google Calendar API**.
3. **OAuth consent screen**: External; agrega tu correo como *test user* mientras esté en pruebas.
4. **Credentials → Create credentials → OAuth client ID → Web application**.
   - **Authorized redirect URI:** `https://s4bdashboard.onrender.com/oauth/google/callback`
5. Variables en Render:
```
GOOGLE_OAUTH_ENABLED = true
GOOGLE_CLIENT_ID     = <client id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET = <client secret>
GOOGLE_REDIRECT_URI  = https://s4bdashboard.onrender.com/oauth/google/callback
```

---

## C) Cualquier otro correo — IMAP (Yahoo, iCloud, Zoho, hosting, empresa…)

**No requiere registrar ninguna app.** El usuario entra a **Integraciones →
Conectar correo → “Otro correo (IMAP)”**, elige su proveedor (o pone el servidor),
y escribe **su correo + contraseña**. Listo, queda conectado automáticamente.

- La contraseña se guarda **cifrada (AES-256-GCM)** y se usa solo para leer la bandeja.
- Presets incluidos: Yahoo, iCloud, Zoho, GoDaddy, Hostinger, y “personalizado”.
- IMAP trae **correo** (no calendario; eso solo lo dan Outlook/Gmail por OAuth).

### ⚠️ Importante sobre “solo usuario y contraseña”
- **Yahoo, iCloud, Zoho, hosting/empresa:** funcionan con IMAP. Muchos exigen una
  **“contraseña de aplicación”** (se genera en la config de seguridad del correo,
  normalmente con verificación en 2 pasos activada) en lugar de la contraseña normal.
- **Gmail y Outlook/Microsoft 365:** por seguridad **ya NO aceptan la contraseña
  normal por IMAP**. Por eso para esos dos lo correcto es **OAuth** (secciones A y B):
  un clic, sin generar contraseñas. (Gmail sí admite IMAP con *app password* si el
  usuario tiene 2FA, pero OAuth es mejor experiencia.)

**Resumen:** Gmail/Outlook → botón OAuth (1 clic). Todos los demás → IMAP con
correo + contraseña (de aplicación).

## Probar
1. Render **Live** → portal → **Integraciones → Conectar correo → Conectar (Outlook)**.
2. Autoriza en Microsoft → te regresa al portal con “Correo conectado”.
3. **Casos de uso → Resumen de correo y agenda** → elige salida → **Generar resumen**.
4. Sale el resumen real de tu bandeja + agenda, descargable en Word/PDF. 🎉

## Notas
- Sin estas variables, el botón **Conectar** aparece como **“no configurado”** (no rompe nada).
- Los tokens se guardan **cifrados (AES-256-GCM)** y se **refrescan solos**.
- El contenido del correo se procesa por el enrutador de privacidad (igual que el resto).
- La `REDIRECT_URI` en Render **debe coincidir exactamente** con la registrada en Azure/Google.

_MaestroAI · Guía de conexión de correo (OAuth)._
