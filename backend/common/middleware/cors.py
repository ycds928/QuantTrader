from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from ..config import get_settings


def setup_cors(app: FastAPI) -> None:
    settings = get_settings()
    origins = [origin.strip() for origin in settings.API_CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
