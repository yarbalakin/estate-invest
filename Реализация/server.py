#!/usr/bin/env python3
"""
FastAPI сервер для таблицы риелторов Estate Invest.
GET  /          → отдаёт риелторы.html (требует Basic Auth)
POST /refresh   → запускает generate_svodka.py (требует Basic Auth)
"""
import subprocess
import secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI(docs_url=None, redoc_url=None)
security = HTTPBasic()

BASE_DIR = Path(__file__).parent
HTML_FILE = BASE_DIR / "риелторы.html"
SCRIPT = BASE_DIR / "generate_svodka.py"

# Логин/пароль — меняй здесь
AUTH_USER = "estate"
AUTH_PASS = "ei2026"


def check_auth(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username.encode(), AUTH_USER.encode())
    ok_pass = secrets.compare_digest(creds.password.encode(), AUTH_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


@app.get("/", response_class=HTMLResponse)
def index(user: str = Depends(check_auth)):
    if not HTML_FILE.exists():
        raise HTTPException(status_code=404, detail="риелторы.html не найден — запусти /refresh")
    return HTML_FILE.read_text(encoding="utf-8")


_refresh_running = False
_refresh_log = ""

def _run_script():
    global _refresh_running, _refresh_log
    _refresh_running = True
    _refresh_log = "Запущено..."
    try:
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
        _refresh_log = result.stdout[-3000:] + (result.stderr[-500:] if result.returncode != 0 else "")
    except Exception as e:
        _refresh_log = str(e)
    finally:
        _refresh_running = False


@app.post("/refresh")
def refresh(user: str = Depends(check_auth)):
    global _refresh_running
    if _refresh_running:
        return {"ok": False, "running": True, "msg": "Уже обновляется, подождите"}
    import threading
    threading.Thread(target=_run_script, daemon=True).start()
    return {"ok": True, "running": True, "msg": "Запущено в фоне (~2 мин)"}


@app.get("/refresh/status")
def refresh_status(user: str = Depends(check_auth)):
    return {"running": _refresh_running, "log": _refresh_log[-1000:]}


@app.get("/health")
def health():
    return {"ok": True}
