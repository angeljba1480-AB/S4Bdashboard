"""Conector SFTP de **solo lectura** para sistemas legados sin API.

Trae un archivo o el contenido de un directorio remoto. paramiko se importa de forma
perezosa para que la app cargue aunque no esté instalado (en prod sí está, ver
requirements.txt). Nunca escribe en el servidor remoto.
"""
from __future__ import annotations

import io
import posixpath
import stat

MAX_FILES = 25
MAX_BYTES = 20 * 1024 * 1024  # 20 MB por archivo
# Extensiones cuyo texto sabemos extraer (ingest.extract_text) o leer directo.
TEXT_EXT = (".txt", ".csv", ".md", ".json", ".log", ".xml", ".pdf", ".docx")


def _connect(host: str, port: int, username: str, auth_type: str, secret: str):
    import paramiko  # lazy

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if auth_type == "key":
        pkey = None
        for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
            try:
                pkey = cls.from_private_key(io.StringIO(secret))
                break
            except Exception:
                continue
        if pkey is None:
            raise RuntimeError("Llave privada no válida (se esperaba RSA/Ed25519/ECDSA en PEM).")
        ssh.connect(host, port=int(port or 22), username=username, pkey=pkey, timeout=20)
    else:
        ssh.connect(host, port=int(port or 22), username=username, password=secret, timeout=20)
    return ssh


def list_files(host: str, port: int, username: str, auth_type: str, secret: str,
               remote_path: str) -> list[dict]:  # pragma: no cover - network
    """Lista archivos (no recursivo) del path remoto (archivo o directorio)."""
    ssh = _connect(host, port, username, auth_type, secret)
    try:
        sftp = ssh.open_sftp()
        try:
            st = sftp.stat(remote_path)
            if stat.S_ISDIR(st.st_mode):
                out = [{"name": a.filename, "size": a.st_size}
                       for a in sftp.listdir_attr(remote_path) if not stat.S_ISDIR(a.st_mode)]
                return out[:MAX_FILES]
            return [{"name": posixpath.basename(remote_path), "size": st.st_size}]
        finally:
            sftp.close()
    finally:
        ssh.close()


def fetch(host: str, port: int, username: str, auth_type: str, secret: str,
          remote_path: str) -> list[tuple[str, bytes]]:  # pragma: no cover - network
    """Descarga el archivo (o los archivos soportados del directorio). (nombre, bytes)."""
    ssh = _connect(host, port, username, auth_type, secret)
    out: list[tuple[str, bytes]] = []
    try:
        sftp = ssh.open_sftp()
        try:
            st = sftp.stat(remote_path)
            if stat.S_ISDIR(st.st_mode):
                paths = [posixpath.join(remote_path, a.filename)
                         for a in sftp.listdir_attr(remote_path)
                         if not stat.S_ISDIR(a.st_mode) and a.filename.lower().endswith(TEXT_EXT)]
            else:
                paths = [remote_path]
            for p in paths[:MAX_FILES]:
                if sftp.stat(p).st_size > MAX_BYTES:
                    continue
                buf = io.BytesIO()
                sftp.getfo(p, buf)
                out.append((posixpath.basename(p), buf.getvalue()))
        finally:
            sftp.close()
    finally:
        ssh.close()
    return out
