"""
QLPT-AI — Quản lý phòng trọ và điện nước tích hợp AI
Khởi chạy: python main.py
"""
import os
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import init_db, SessionLocal

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


# ── Lifespan (thay thế on_event deprecated) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo DB và seed dữ liệu mẫu khi app khởi động."""
    init_db()
    from app.seed import seed_if_empty
    from app.seed_demo import ensure_demo_history
    db = SessionLocal()
    try:
        if os.getenv("SEED_DEMO_DATA", "1") != "0":
            seed_if_empty(db)
            # DB đã có dữ liệu (seed_if_empty bỏ qua) vẫn được bù lịch sử demo.
            ensure_demo_history(db)
    finally:
        db.close()
    yield
    # (cleanup khi shutdown nếu cần)


app = FastAPI(
    title="QLPT-AI — Quản lý phòng trọ và điện nước",
    description="Quản lý chỉ số, hóa đơn, thanh toán và phân tích AI",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Không cache giao diện (tránh trình duyệt giữ CSS/JS cũ sau khi cập nhật) ──
@app.middleware("http")
async def no_cache_ui_assets(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.middleware("http")
async def security_headers(request, call_next):
    """Thêm header bảo mật cơ bản cho mọi response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )
    if os.getenv("ENABLE_HSTS") == "1":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

# ── Routers KT2 + KT3 ────────────────────────────────────────────────────────
from app.routers import auth, households, meters, readings, prices, invoices, payments
from app.routers import ai_analysis, chat

app.include_router(auth.router,          prefix="/api/auth",       tags=["Auth"])
app.include_router(households.router,    prefix="/api/households", tags=["Hộ/Phòng"])
app.include_router(meters.router,        prefix="/api/meters",     tags=["Đồng hồ"])
app.include_router(readings.router,      prefix="/api/readings",   tags=["Chỉ số"])
app.include_router(prices.router,        prefix="/api/prices",     tags=["Đơn giá"])
app.include_router(invoices.router,      prefix="/api/invoices",   tags=["Hóa đơn"])
app.include_router(payments.router,      prefix="/api/payments",   tags=["Thanh toán"])
app.include_router(ai_analysis.router,   prefix="/api/ai",         tags=["AI Phân tích"])
app.include_router(chat.router,          prefix="/api/chat",       tags=["Chat AI"])

# ── Static files ─────────────────────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
serve_frontend = os.getenv("SERVE_FRONTEND", "1") != "0"
if serve_frontend and os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    if not serve_frontend:
        api_port = os.getenv("UTILITY_API_PORT", "8001")
        return HTMLResponse(content=f"<h1>QLPT-AI API is running</h1><p>Frontend: http://localhost:5500</p><p>API docs: <a href='http://localhost:{api_port}/docs'>API docs</a></p>")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Utility Management System</h1>")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Hệ thống hoạt động bình thường"}


@app.get("/api/info")
async def system_info():
    return {
        "name": "QLPT-AI — Quản lý phòng trọ và điện nước",
        "version": "1.0.0",
        "phase": "KT2 — CRUD API và Frontend",
        "db": os.getenv("DATABASE_URL", "sqlite:///./utility_mgmt.db"),
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("UTILITY_API_HOST", "0.0.0.0"),
        port=int(os.getenv("UTILITY_API_PORT", "8001")),
        reload=os.getenv("UTILITY_API_RELOAD", "0") == "1",
    )
