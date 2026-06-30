"""QA end-to-end de flujos internos (sin cuentas externas). Imprime PASS/FAIL."""
import io, json, os, tempfile, zipfile

_fd, _p = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_p}"

from fastapi.testclient import TestClient
from app.main import app

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

c = TestClient(app)
with c:
    tok = c.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    # 1. Documentos: subir txt, xlsx, zip
    r = c.post("/documents/upload", headers=h, files={"file": ("nota.txt", b"contrato de prueba", "text/plain")}, data={"area": "Legal"})
    check("Subir .txt", r.status_code == 201 and r.json().get("indexed"), r.text[:80])
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(["Cliente", "Venta"]); ws.append(["IMSS", 1000]); b = io.BytesIO(); wb.save(b)
    r = c.post("/documents/upload", headers=h, files={"file": ("datos.xlsx", b.getvalue(), "application/octet-stream")})
    check("Subir .xlsx (extrae texto)", r.status_code == 201, r.text[:80])
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w") as z: z.writestr("a.txt", "alpha"); z.writestr("b.csv", "x,y\n1,2")
    r = c.post("/documents/upload", headers=h, files={"file": ("paq.zip", zb.getvalue(), "application/zip")})
    check("Subir .zip (expande)", r.status_code == 201, r.text[:80])

    # 2. Export de reporte (pdf, docx)
    for fmt in ("pdf", "docx", "pptx", "xlsx"):
        r = c.post("/export/report", headers=h, json={"title": "Reporte QA", "content": "Línea 1\nLínea 2", "format": fmt})
        check(f"Export {fmt}", r.status_code == 200 and len(r.content) > 200, f"{r.status_code} {len(r.content)}b")

    # 3. Automatización multi-paso: notify -> ai -> deliver
    a = c.post("/automations", headers=h, json={"name": "QA pipeline", "trigger": "manual", "action_type": "notify"}).json()
    steps = [{"type": "notify", "message": "Cobranza: 3 vencidos."}, {"type": "ai", "prompt": "Redacta recordatorio."}, {"type": "deliver", "channels": ["notify"]}]
    r = c.put(f"/automations/{a['id']}/steps", headers=h, json={"steps": steps})
    check("Pipeline guarda 3 pasos", r.status_code == 200 and len(r.json()["config"]["steps"]) == 3)
    run = c.post(f"/automations/{a['id']}/run", headers=h).json()
    check("Pipeline corre y entrega", run.get("status") == "completed" and "enviado a" in run.get("detail", ""), run.get("detail", "")[:100])

    # 4. Validate (canvas) muestra pasos
    v = c.post("/automations/from-template", headers=h, json={"template_id": "reporte_operacion"}).json()
    val = c.get(f"/automations/{v['id']}/validate", headers=h).json()
    check("Validate trae diagrama", val.get("steps") and any(s["label"] == "Salida" for s in val["steps"]))
    rm = c.post(f"/automations/{v['id']}/run", headers=h).json()
    check("Workflow 'mando' nativo entrega", "enviado a" in rm.get("detail", ""), rm.get("detail", "")[:80])

    # 5. Finanzas: plantilla -> cargar JSON -> overview refleja -> borrar
    r = c.get("/finance/dataset/template", headers=h)
    check("Finanzas: descargar plantilla", r.status_code == 200 and "company" in r.json())
    payload = json.dumps({"company": {"name": "ACME QA", "legalName": "ACME", "period": "2025", "ceo": "", "cfo": ""}})
    r = c.post("/finance/dataset", headers=h, files=[("files", ("d.json", payload.encode(), "application/json"))])
    check("Finanzas: cargar JSON", r.status_code == 201, r.text[:80])
    ov = c.get("/finance/overview?entity=CONS", headers=h).json()
    check("Finanzas: overview refleja carga", ov["company"]["name"] == "ACME QA" and ov["is_demo"] is False)
    check("Finanzas: restablecer", c.delete("/finance/dataset", headers=h).json().get("ok"))

    # 6. KEDB: habilitar perfil -> alta -> analyze -> promote -> proposals -> approve
    c.put("/company/profile", headers=h, json={"industry": "Ciberseguridad / SOC"})
    check("KEDB: gateado por perfil cyber", c.get("/kedb/status", headers=h).json().get("enabled"))
    k = c.post("/kedb", headers=h, json={"title": "Falso positivo EDR", "symptom": "EDR bloquea binario firmado", "resolution": "excluir hash", "product": "EDR", "severity": "high"}).json()
    an = c.post("/kedb/analyze", headers=h, json={"symptom": "el EDR bloquea un binario firmado", "product": "EDR"}).json()
    check("KEDB: analyze reconoce", an.get("is_known") and an.get("matches"))
    cand = c.post(f"/kedb/{k['id']}/promote", headers=h).json()
    check("KEDB: promover (shared/pending)", cand.get("scope") == "shared")
    props = c.get("/kedb/proposals", headers=h).json()
    check("KEDB: propuesta visible al operador", any(p["id"] == cand["id"] for p in props))
    appr = c.post(f"/kedb/proposals/{cand['id']}/approve", headers=h).json()
    check("KEDB: aprobar -> publicado", appr.get("status") == "published")
    lst = c.get("/kedb", headers=h).json()
    check("KEDB: shared visible en lista", any(x["id"] == cand["id"] and x["scope"] == "shared" for x in lst))

    # 7. Vector store por defecto in-process
    sec = c.get("/admin/security", headers=h).json()
    check("RAG vector store activo", bool(sec.get("vector_store")), str(sec.get("vector_store")))

# Resumen
ok = sum(1 for _, p, _ in results if p)
print(f"\n=== QA E2E: {ok}/{len(results)} PASS ===")
for name, p, det in results:
    print(f"[{'PASS' if p else 'FALLA'}] {name}" + (f"  · {det}" if (det and not p) else ""))
import sys; sys.exit(0 if ok == len(results) else 1)
