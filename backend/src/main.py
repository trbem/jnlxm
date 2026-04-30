import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from config import settings
from src.models.database import init_db
from src.api import (
    device_router,
    member_router,
    log_router,
    stats_router,
    config_router,
    auth_router,
    notification_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="家庭监控智能助手 API",
    description="基于 ESP32-S3-EYE 的人脸识别家庭监控系统后端 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

app.include_router(device_router)
app.include_router(member_router)
app.include_router(log_router)
app.include_router(stats_router)
app.include_router(config_router)
app.include_router(auth_router)
app.include_router(notification_router)


@app.get("/")
async def root():
    return {
        "name": "家庭监控智能助手 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
