"""
WebScribe FastAPI Application

Main application entry point that wires all API routers and handles startup/shutdown events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_db_and_tables
from api.scrape import router as scrape_router
from api.jobs import router as jobs_router
from api.notes import router as notes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database schema and seed templates
    - Shutdown: Clean up resources
    """
    # Startup: Initialize database
    print("🚀 Starting WebScribe API...")
    create_db_and_tables()
    print("✓ Database initialized")

    yield

    # Shutdown
    print("👋 Shutting down WebScribe API...")


# Create FastAPI app
app = FastAPI(
    title="WebScribe API",
    description="Convert messy web pages into clean, structured Markdown notes",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(scrape_router)
app.include_router(jobs_router)
app.include_router(notes_router)


@app.get("/")
def root():
    """Root endpoint - health check"""
    return {
        "service": "WebScribe API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload during development
    )
