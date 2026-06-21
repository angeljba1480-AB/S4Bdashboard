# MCP curado de trámites (jerárquico)

Base de conocimiento **curada** de trámites que aterriza las respuestas de
agentes y casos de uso, en **capas**:

1. **País** — trámites nacionales (`app/regional/tramites.py`, scope `nacional`).
2. **Estado/Municipio** — curados por región (scope `estatal`/`municipal`).
3. **Empresa (tenant)** — capa **privada** del cliente que paga
   (`TenantTramite`); se agrega en *Admin → MCP de empresa · Trámites*.

El grounding combina **empresa → estado → país** (la capa privada manda) y cita
autoridad/fuente. La misma KB se consulta por:

- La plataforma: `GET /tramites?q=&region=&municipio=&country=` (merge en capas) y
  el pre-llenado de casos de uso (`recipes`).
- El **servidor MCP**: `app/mcp/tramites_server.py` (FastMCP), con herramientas
  `search_tramites`, `get_tramite_detail`, `tramite_context`, `list_countries`.

## Despliegue del MCP (uno por país/estado y por empresa)
```bash
pip install -r apps/api/requirements-mcp.txt

# Instancia por PAÍS (filtra por estado vía argumento de la tool):
PAI_MCP_COUNTRY=MX python -m app.mcp.tramites_server

# Instancia por EMPRESA que paga (suma su capa privada vía API + token):
PAI_API_BASE=https://api.tu-saas.com PAI_TOKEN=<token_tenant> \
  python -m app.mcp.tramites_server
```
Así tienes **un MCP por país** (y por estado al filtrar) y **uno por cada empresa**
que incluye su contexto privado encima de los curados.
