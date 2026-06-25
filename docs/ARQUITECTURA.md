# Arquitectura y funcionalidades — MaestroAI

> Diagramas (Mermaid) de la plataforma. Se renderizan automáticamente en GitHub.
> Reflejan el código real. Última actualización: 2026-06-25.

---

## 1. Arquitectura por capas

```mermaid
flowchart TD
  U["👤 Usuario"] --> WEB["Portal Next.js · Vercel"]
  WEB -->|"HTTPS + JWT"| API["API FastAPI · Render"]

  API --> AUTH["Auth multi-tenant · RBAC por área y licencia"]
  AUTH --> POL["Policy Engine · Clasificador · DLP/PII"]
  POL --> ROUTER["🔀 Privacy Model Router"]

  ROUTER --> RAG[("RAG cifrado · pgvector")]
  ROUTER --> MEM[("Memoria + Tags")]
  ROUTER --> TOOLS["Toolkit acciones Google/MS"]
  ROUTER --> WF["Workflows · n8n"]
  ROUTER --> MODELS{"Capa de modelos"}

  MODELS --> LOCAL["Local / self-hosted"]
  MODELS --> VPC["VPC privada"]
  MODELS --> OPEN["Abierto / NaN"]
  MODELS --> PREM["Premium · GPT / Claude / DeepSeek"]

  API --> AUD[("Auditoría · costo · tokens")]
  DB[("Postgres")] -.-> API

  classDef priv fill:#dcfce7,stroke:#16a34a;
  classDef ext fill:#ede9fe,stroke:#7c3aed;
  class LOCAL,VPC priv;
  class OPEN,PREM ext;
```

🟩 verde = privado (no sale de tu infraestructura) · 🟪 morado = externo (con PII redactada).

---

## 2. Privacy Model Router (decisión de ruta)

```mermaid
flowchart TD
  A["Prompt + contexto"] --> C["Clasificar sensibilidad + detectar PII"]
  C --> P{"¿Viola política?"}
  P -->|"Sí"| BLOCK["🚫 Bloquear + auditar"]
  P -->|"No"| MIN["Minimizar + redactar PII"]
  MIN --> R{"Nivel de sensibilidad"}
  R -->|"RESTRICTED"| L["Local · sin salida externa"]
  R -->|"CONFIDENTIAL"| Vq{"¿VPC permitida?"}
  Vq -->|"Sí"| VPC["VPC privada"]
  Vq -->|"No"| L
  R -->|"PII presente"| Vq
  R -->|"INTERNAL / PUBLIC"| E{"¿Razonamiento premium?"}
  E -->|"Sí"| PREM["Premium externo"]
  E -->|"No"| OPEN["Modelo abierto · costo"]
  L --> OUT["Respuesta + auditoría"]
  VPC --> OUT
  PREM --> OUT
  OPEN --> OUT
```

Regla de oro: *si no es indispensable enviar el dato, no se envía.*

---

## 3. Cascada de modelos + eficiencia de tokens

```mermaid
flowchart TD
  Q["Consulta / caso"] --> BASE["Genera con modelo barato · NaN/open"]
  BASE --> INS{"¿Insuficiente, avanzado o máxima precisión?"}
  INS -->|"No"| OUT["Resultado"]
  INS -->|"Sí"| PA{"¿Hay proveedor premium?"}
  PA -->|"No"| OUT
  PA -->|"Sí"| SENS{"¿Contenido sensible?"}
  SENS -->|"Sí, sin aprobar"| ASK["Pedir aprobación al usuario"]
  SENS -->|"No / aprobado"| COND["Condensar contexto con modelo barato"]
  COND --> BUD{"¿Dentro del tope de tokens?"}
  BUD -->|"No"| OUT
  BUD -->|"Sí"| REF["Refinar con premium"]
  REF --> OUT2["Resultado refinado + auditado"]
```

Idea: el PDF grande lo digiere el modelo barato; el premium solo ve el extracto chico → más barato y privado.

---

## 4. Caso de uso (receta) de punta a punta

```mermaid
flowchart TD
  ON{"¿Onboarding completo?"} -->|"No"| BLK["Bloquea casos · pide info base"]
  ON -->|"Sí"| OBJ["Objetivo + notas + formato de salida"]
  OBJ --> IN["Datos mínimos del caso"]
  IN --> GRD["Grounding: RAG por categoría + perfil de empresa + trámites"]
  GRD --> ROUTE["Privacy Router"]
  ROUTE --> DRAFT["Borrador con IA"]
  DRAFT --> CASC["Cascada opcional · refinar premium"]
  CASC --> REV["Revisas y apruebas"]
  REV --> OUTP["Entregable: PDF / Word / PPTX / XLSX"]
  OUTP --> MEMC["Auto-guarda en Memoria + Tags"]
  OUTP --> AUDc["Auditoría"]
```

---

## 5. Toolkit de acciones (Google / Microsoft)

```mermaid
flowchart TD
  ACT["Elegir acción · enviar correo, evento, Sheets, Teams"] --> RW{"¿Es de escritura?"}
  RW -->|"Lectura"| EXEC["Ejecuta ahora"]
  RW -->|"Escritura"| GR{"¿Permitida siempre?"}
  GR -->|"Sí"| EXEC
  GR -->|"No"| PEND["Solicitud pendiente"]
  PEND --> APP{"Decisión del usuario"}
  APP -->|"Aprobar"| EXEC
  APP -->|"Aprobar y permitir siempre"| GRANT["Crea autorización permanente"]
  GRANT --> EXEC
  APP -->|"Rechazar"| REJ["Rechazada"]
  EXEC --> AUDa["Auditoría"]
```

---

## 6. Mapa de funcionalidades

```mermaid
mindmap
  root(("MaestroAI"))
    Datos
      Documentos por área
      Catálogo de categorías
      Tratamiento público/privado
      RAG cifrado
      Google Drive
    Casos de uso
      Objetivo + notas + formato
      Reportes por industria
      Export PDF/Word/PPTX/XLSX
      Grounding por categoría
    Conversación
      Chat 3 modos de contexto
      Notebooks
      Memoria + Tags
    Modelos
      Privacy Router
      LLMs externos
      Cascada
      Eficiencia de tokens
    Integraciones
      Correo Outlook/Gmail/IMAP
      Toolkit de acciones
      Conectores REST / Webhooks
      n8n
    Gobierno
      Super admin
      Permisos por área y licencia
      Auditoría navegable
      Dashboard
      Flujogramas
```

---

## 7. Modelo de datos (principal)

```mermaid
erDiagram
  TENANT ||--o{ USER : "tiene"
  TENANT ||--o{ DOCUMENT : "posee"
  TENANT ||--o{ DOCUMENT_CATEGORY : "cataloga"
  TENANT ||--o{ OAUTH_TOKEN : "conecta"
  USER ||--o{ NOTEBOOK : "crea"
  USER ||--o{ MEMORY_ITEM : "guarda"
  USER ||--o{ ACTION_REQUEST : "solicita"
  USER ||--o{ ACTION_GRANT : "autoriza"
  DOCUMENT ||--o{ DOCUMENT_CHUNK : "se indexa en"
  TENANT ||--o{ AUDIT_EVENT : "registra"
  TENANT ||--o{ PROVIDER_SETTING : "configura"

  DOCUMENT {
    string id
    string area
    string category
    string sensitivity
  }
  MEMORY_ITEM {
    string id
    string title
    string tags
    string area
  }
  ACTION_REQUEST {
    string action
    string status
  }
```

---

## 8. Despliegue

```mermaid
flowchart LR
  GH["GitHub · rama main"] -->|"push"| V["Vercel · build portal"]
  GH -->|"push"| R["Render · build API"]
  V --> PORTAL["Portal en vivo"]
  R --> APILIVE["API en vivo"]
  APILIVE --- PG[("Postgres")]
  PORTAL -->|"HTTPS"| APILIVE
```

_MaestroAI · Arquitectura y funcionalidades._
