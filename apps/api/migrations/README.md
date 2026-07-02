# Migraciones (Alembic)

Alembic es la **fuente de verdad del esquema en producción**. En dev/tests se sigue usando
`create_all` (rápido); en `APP_ENV=production`, `init_db()` corre `alembic upgrade head`
automáticamente al arrancar (con sellado del baseline si la BD es legacy).

## Flujo al cambiar un modelo (apps/api/app/models.py)
```bash
cd apps/api
# 1) genera la migración comparando modelos vs BD
DATABASE_URL="sqlite:////tmp/dev.db" alembic revision --autogenerate -m "describe el cambio"
# 2) REVISA el archivo generado en migrations/versions/ (autogenerate no es perfecto)
# 3) aplícala en tu dev
DATABASE_URL="sqlite:////tmp/dev.db" alembic upgrade head
```
El test `tests/test_migrations.py` falla si cambiaste un modelo sin crear su migración
(drift de tablas/columnas), así que el CI te obliga a mantenerlas al día.

## Comandos útiles
```bash
alembic upgrade head          # aplicar todo
alembic downgrade -1          # revertir la última
alembic current               # revisión actual de la BD
alembic history               # historial
alembic stamp head            # marcar como aplicado SIN ejecutar (BD legacy)
```

## Producción
- `init_db()` aplica migraciones solo. NO uses `create_all` en prod.
- **BD nueva:** aplica el baseline + posteriores.
- **BD legacy** (creada con `create_all` antes de Alembic): al primer arranque se sella en
  el baseline (revisión raíz) y luego aplica lo pendiente — no recrea tablas.
- La URL sale de `settings.database_url` (env/.env), no de `alembic.ini`.
- pgvector: además de las migraciones, corre una vez `infra/supabase/001_pgvector.sql`
  para la extensión y el índice vectorial (`VECTOR_STORE=pgvector`).
