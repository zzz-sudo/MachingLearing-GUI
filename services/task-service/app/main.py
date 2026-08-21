from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.errors import WorkspaceServiceError
from app.routes import router
from app.settings import resolve_data_dir
from app.storage import WorkspaceStore
from app.training import TrainingService


def create_app(data_dir: Path | None = None) -> FastAPI:
    resolved_data_dir = data_dir or resolve_data_dir()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configured_project = Path(os.environ["ML_GUI_DEFAULT_PROJECT_DIR"]).expanduser().resolve() if os.environ.get("ML_GUI_DEFAULT_PROJECT_DIR") else None
        repository_project = Path(__file__).resolve().parents[3] / "workspace" / "default"
        default_project = configured_project or (repository_project if data_dir is None and repository_project.exists() else None)
        store = WorkspaceStore(resolved_data_dir, default_project_dir=default_project)
        store.initialize()
        application.state.workspace_store = store
        application.state.training_service = TrainingService(store)
        yield

    application = FastAPI(
        title="MachingLearing GUI Task Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://tauri.localhost",
            "tauri://localhost",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router, prefix="/api")

    @application.exception_handler(WorkspaceServiceError)
    async def handle_workspace_error(
        _request: Request,
        error: WorkspaceServiceError,
    ) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=error.as_response())

    return application


app = create_app()
