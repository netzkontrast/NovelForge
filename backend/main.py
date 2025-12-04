import os, sys
from dotenv import load_dotenv

def _load_env_from_nearby():
    candidates = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, ".env"))
    backend_dir = os.path.abspath(os.path.dirname(__file__))
    candidates.append(os.path.join(backend_dir, ".env"))
    candidates.append(os.path.join(os.getcwd(), ".env"))
    for p in candidates:
        try:
            if os.path.isfile(p):
                load_dotenv(p, override=False)
        except Exception:
            pass

_load_env_from_nearby()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select

from app.api.router import api_router
from app.db.session import engine
from app.db import models
from app.bootstrap.init_app import init_prompts, create_default_card_types
# Knowledge Base Initialization
from app.bootstrap.init_app import init_knowledge
from app.bootstrap.init_app import init_reserved_project
from app.bootstrap.init_app import init_workflows

def init_db():
    models.SQLModel.metadata.create_all(engine)

# Create all tables
# models.Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

# Use lifespan event handler instead of on_event
@asynccontextmanager
async def lifespan(app):
    # Run on startup
    # Ensure all tables exist (Available for development; production suggests migration via Alembic)
    models.SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        init_prompts(session)
        create_default_card_types(session)
        # Initialize Knowledge Base
        init_knowledge(session)
        # Initialize reserved project
        init_reserved_project(session)
        # Initialize built-in workflows
        init_workflows(session)
    yield
    # Cleanup logic can be added on shutdown (if needed)

# Create FastAPI app instance, register lifespan
app = FastAPI(
    title="NovelForge API",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Set CORS middleware, allow requests from all origins
# This is convenient in development, but should be stricter in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["X-Workflows-Started"],  # Allow browser to read this custom response header
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to NovelCreationEditor API"}

if __name__ == "__main__":
    import uvicorn
    # Add reload=True, so that when code is modified it will automatically reload
    # Configure shorter graceful shutdown time, easy to exit quickly with Ctrl+C
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        timeout_graceful_shutdown=1,
    )

