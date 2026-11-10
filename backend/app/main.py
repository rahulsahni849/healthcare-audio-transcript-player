from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import audio as audio_api
from app.api import download as download_api
from app.api import recordings as recordings_api
from app.core.config import settings
from app.services.manifest import ManifestError


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Scribble Audio Player API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "Accept-Ranges", "ETag", "Content-Length"],
    )

    app.include_router(recordings_api.router, prefix="/api")
    app.include_router(audio_api.router, prefix="/api")
    app.include_router(download_api.router, prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.exception_handler(ManifestError)
    def manifest_error_handler(request: Request, exc: ManifestError):
        return JSONResponse(
            status_code=503,
            content={"detail": {"code": "MANIFEST_UNAVAILABLE", "message": str(exc)}},
        )

    return app


app = create_app()
