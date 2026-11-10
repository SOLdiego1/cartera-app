import os
import shutil
import io
import time
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from parser import parse_cartera_pdf, calculate_aging_for_date
from whatsapp_service import generate_all_whatsapp_options, generate_whatsapp_message_by_color
from excel_service import generate_excel_cartera
from pdf_client_service import generate_client_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app = FastAPI(title="Cartera & Vencimientos - Agroindustriales Cañaveralejo")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

SESSION_COOKIE_NAME = "cartera_session_id"
DEFAULT_DATA = None
DEFAULT_FILENAME = None

# In-memory session store: each seller has their own isolated parsed portfolio data
# SESSIONS[session_id] = {
#     "current_file": str,
#     "parsed_data": dict,
#     "filename": str,
#     "is_custom": bool,
#     "updated_at": float
# }
SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_default_pdf():
    files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f)) and f.lower().endswith(".pdf")]
    if files:
        return os.path.join(DATA_DIR, files[0])
    return None

def load_default_data():
    global DEFAULT_DATA, DEFAULT_FILENAME
    default_pdf = get_default_pdf()
    if default_pdf and os.path.exists(default_pdf):
        DEFAULT_DATA = parse_cartera_pdf(default_pdf)
        DEFAULT_FILENAME = os.path.basename(default_pdf)

@app.on_event("startup")
def startup_event():
    load_default_data()

def resolve_session_id(request: Request, session_id: Optional[str] = None) -> str:
    # 1. Query parameter
    if session_id and len(session_id.strip()) >= 8:
        return session_id.strip()
    # 2. Custom header
    hdr = request.headers.get("X-Session-ID")
    if hdr and len(hdr.strip()) >= 8:
        return hdr.strip()
    # 3. Cookie
    cookie_val = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_val and len(cookie_val.strip()) >= 8:
        return cookie_val.strip()
    # 4. Generate new session ID
    return f"vendedor_{uuid.uuid4().hex[:12]}"

def get_session_info(sid: str):
    # Cleanup sessions older than 7 days
    now = time.time()
    for old_sid in list(SESSIONS.keys()):
        if now - SESSIONS[old_sid].get("updated_at", now) > 7 * 86400:
            SESSIONS.pop(old_sid, None)

    if sid in SESSIONS and SESSIONS[sid].get("parsed_data"):
        sess = SESSIONS[sid]
        return sess["parsed_data"], sess.get("filename", "Reporte Subido"), True

    # Fallback to default demo report
    if DEFAULT_DATA is None:
        load_default_data()
    return DEFAULT_DATA, DEFAULT_FILENAME or "Reporte Base Demo", False

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    sid = resolve_session_id(request)
    response = templates.TemplateResponse(request=request, name="index.html")
    response.set_cookie(SESSION_COOKIE_NAME, sid, max_age=30*24*3600, samesite="lax")
    return response

@app.get("/api/data")
async def get_portfolio_data(
    request: Request,
    review_date: Optional[str] = Query(None, description="Fecha de corte YYYY-MM-DD"),
    session_id: Optional[str] = Query(None)
):
    sid = resolve_session_id(request, session_id)
    parsed, filename, is_custom = get_session_info(sid)
    if not parsed:
        resp = JSONResponse({"status": "no_data", "message": "No hay datos de cartera disponibles."})
        resp.set_cookie(SESSION_COOKIE_NAME, sid, max_age=30*24*3600, samesite="lax")
        return resp

    target_date = review_date if review_date else parsed["metadata"]["report_date"]
    calculated = calculate_aging_for_date(parsed, target_date)
    calculated["session"] = {
        "session_id": sid,
        "filename": filename,
        "is_custom": is_custom
    }

    resp = JSONResponse(calculated)
    resp.set_cookie(SESSION_COOKIE_NAME, sid, max_age=30*24*3600, samesite="lax")
    return resp

@app.post("/api/upload")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .pdf")

    sid = resolve_session_id(request, session_id)
    user_dir = os.path.join(SESSIONS_DIR, sid)
    os.makedirs(user_dir, exist_ok=True)

    save_path = os.path.join(user_dir, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        new_parsed = parse_cartera_pdf(save_path)
        SESSIONS[sid] = {
            "current_file": save_path,
            "parsed_data": new_parsed,
            "filename": file.filename,
            "is_custom": True,
            "updated_at": time.time()
        }
        calculated = calculate_aging_for_date(new_parsed, new_parsed["metadata"]["report_date"])
        calculated["session"] = {
            "session_id": sid,
            "filename": file.filename,
            "is_custom": True
        }
        resp = JSONResponse({
            "status": "success",
            "message": f"Reporte '{file.filename}' cargado exitosamente para tu sesión privada.",
            "session_id": sid,
            "data": calculated
        })
        resp.set_cookie(SESSION_COOKIE_NAME, sid, max_age=30*24*3600, samesite="lax")
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar el PDF de Siesa: {str(e)}")

@app.post("/api/reset-session")
async def reset_session(request: Request, session_id: Optional[str] = Query(None)):
    sid = resolve_session_id(request, session_id)
    if sid in SESSIONS:
        SESSIONS.pop(sid, None)
    return {"status": "success", "message": "Sesión restablecida al reporte de ejemplo."}

@app.get("/api/files")
async def list_files(request: Request, session_id: Optional[str] = Query(None)):
    sid = resolve_session_id(request, session_id)
    user_dir = os.path.join(SESSIONS_DIR, sid)
    files = []
    active_file = SESSIONS.get(sid, {}).get("filename", "")
    if os.path.exists(user_dir):
        for f in os.listdir(user_dir):
            if f.lower().endswith(".pdf"):
                full_p = os.path.join(user_dir, f)
                files.append({
                    "name": f,
                    "size_kb": round(os.path.getsize(full_p) / 1024, 1),
                    "is_active": f == active_file
                })
    if not files and DEFAULT_FILENAME:
        files.append({
            "name": f"{DEFAULT_FILENAME} (Reporte Ejemplo)",
            "size_kb": round(os.path.getsize(get_default_pdf()) / 1024, 1),
            "is_active": True
        })
    return {"files": files, "active": active_file or DEFAULT_FILENAME}

@app.post("/api/select-file")
async def select_file(request: Request, session_id: Optional[str] = Query(None)):
    payload = await request.json()
    filename = payload.get("filename")
    sid = resolve_session_id(request, session_id)
    user_dir = os.path.join(SESSIONS_DIR, sid)
    target_path = os.path.join(user_dir, filename)

    if not os.path.exists(target_path):
        target_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    new_parsed = parse_cartera_pdf(target_path)
    SESSIONS[sid] = {
        "current_file": target_path,
        "parsed_data": new_parsed,
        "filename": filename,
        "is_custom": True,
        "updated_at": time.time()
    }
    calculated = calculate_aging_for_date(new_parsed, new_parsed["metadata"]["report_date"])
    calculated["session"] = {
        "session_id": sid,
        "filename": filename,
        "is_custom": True
    }
    return {"status": "success", "data": calculated}

@app.get("/api/whatsapp/{nit}")
async def get_whatsapp_data(
    request: Request,
    nit: str,
    review_date: Optional[str] = Query(None),
    color: Optional[str] = Query(None, description="Filtro de color: all, red, yellow, green"),
    session_id: Optional[str] = Query(None)
):
    sid = resolve_session_id(request, session_id)
    parsed, filename, is_custom = get_session_info(sid)
    if not parsed:
        raise HTTPException(status_code=404, detail="Sin datos")

    target_date = review_date if review_date else parsed["metadata"]["report_date"]
    calculated = calculate_aging_for_date(parsed, target_date)

    client = next((c for c in calculated["clients"] if c["nit"] == nit), None)
    if not client:
        raise HTTPException(status_code=404, detail=f"Cliente con NIT {nit} no encontrado")

    all_templates = generate_all_whatsapp_options(
        client=client,
        review_date_str=target_date,
        company_name=parsed["metadata"]["company"]
    )

    selected_key = color if color in ['red', 'yellow', 'green'] else 'all'
    active_message = all_templates[selected_key]

    return {
        "client": {
            "nit": client["nit"],
            "name": client["name"],
            "phone": client["phone"],
            "whatsapp_phone": client["whatsapp_phone"],
            "is_mobile": client["is_mobile"],
            "total_saldo": client["total_saldo"],
            "red_count": client["red_count"],
            "yellow_count": client["yellow_count"],
            "green_count": client["green_count"]
        },
        "review_date": target_date,
        "selected_color": selected_key,
        "active_message": active_message,
        "templates": all_templates
    }

@app.get("/api/client-pdf/{nit}")
async def get_client_pdf(
    request: Request,
    nit: str,
    review_date: Optional[str] = Query(None),
    color: Optional[str] = Query('all', description="Filtro: all, red, yellow, green"),
    session_id: Optional[str] = Query(None)
):
    sid = resolve_session_id(request, session_id)
    parsed, filename, is_custom = get_session_info(sid)
    if not parsed:
        raise HTTPException(status_code=404, detail="Sin datos")

    target_date = review_date if review_date else parsed["metadata"]["report_date"]
    calculated = calculate_aging_for_date(parsed, target_date)

    client = next((c for c in calculated["clients"] if c["nit"] == nit), None)
    if not client:
        raise HTTPException(status_code=404, detail=f"Cliente con NIT {nit} no encontrado")

    pdf_bytes = generate_client_pdf(
        client=client,
        review_date_str=target_date,
        color_filter=color,
        company_name=parsed["metadata"]["company"]
    )

    clean_name = "".join(c for c in client["name"] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    dl_filename = f"Estado_Cuenta_{clean_name}_{color}_{target_date}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dl_filename}"'}
    )

@app.get("/api/export/excel")
async def export_excel(
    request: Request,
    review_date: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    sid = resolve_session_id(request, session_id)
    parsed, filename, is_custom = get_session_info(sid)
    if not parsed:
        raise HTTPException(status_code=404, detail="Sin datos")

    target_date = review_date if review_date else parsed["metadata"]["report_date"]
    calculated = calculate_aging_for_date(parsed, target_date)
    excel_bytes = generate_excel_cartera(calculated)

    dl_filename = f"Cartera_{calculated['metadata']['report_date']}_al_{target_date}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{dl_filename}"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8050, reload=True)
