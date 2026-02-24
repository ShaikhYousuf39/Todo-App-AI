from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import create_db_and_tables
from .api.chat import router as chat_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup: Create database tables
    create_db_and_tables()
    yield
    # Shutdown: Cleanup if needed


app = FastAPI(
    title="Todo AI Chatbot",
    description="AI-powered chatbot for managing todos through natural language",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Todo AI Chatbot"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
