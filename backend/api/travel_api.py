"""FastAPI application factory: CORS, routers, and storage initialization."""

from contextlib import asynccontextmanager

from api import settings
from api.routers import auth, trips, users
from api.storage import get_storage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_storage()  # initialize the active backend (creates JSON files / DB tables)
    yield


def create_app() -> FastAPI:
    # The CORS spec forbids wildcard origins together with credentials, and
    # browsers reject that combination — fail fast rather than ship it.
    if settings.CORS_ALLOW_ORIGINS == ["*"] and settings.CORS_ALLOW_CREDENTIALS:
        raise RuntimeError(
            "CORS misconfiguration: CORS_ALLOW_ORIGINS='*' cannot be combined "
            "with CORS_ALLOW_CREDENTIALS=true. Set explicit origins to use credentials."
        )

    app = FastAPI(
        title="AI Travel Assistant API",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(trips.router)
    app.include_router(users.router)

    @app.get("/", tags=["health"])
    def root() -> dict:
        return {"status": "ok", "service": "ai-travel-assistant-api"}

    return app


app = create_app()
