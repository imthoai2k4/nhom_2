"""
Đề tài 48 — Hệ thống Quản lý Hóa đơn Điện nước Hộ gia đình có Tích hợp AI
Khởi chạy: python main.py
"""
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import init_db, SessionLocal

load_dotenv()


# ── Lifespan (thay thế on_event deprecated) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo DB và seed dữ liệu mẫu khi app khởi động."""
    init_db()
    from app.seed import seed_if_empty
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield
    # (cleanup khi shutdown nếu cần)


app = FastAPI(
    title="Hệ thống Quản lý Hóa đơn Điện nước",
    description="Quản lý chỉ số, hóa đơn, thanh toán và phân tích AI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
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
        "name": "Hệ thống Quản lý Hóa đơn Điện nước",
        "version": "1.0.0",
        "phase": "KT2 — CRUD API và Frontend",
        "db": os.getenv("DATABASE_URL", "sqlite:///./utility_mgmt.db"),
    }


if __name__ == "__main__":
    import webbrowser, threading
    # Mở trình duyệt với tham số phiên bản để không dùng lại HTML cũ trong cache
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000/?v=1.2.0")).start()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
