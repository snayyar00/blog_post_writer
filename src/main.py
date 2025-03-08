"""
Main FastAPI application with blog analysis and keyword research functionality.
Uses functional patterns and dependency injection.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from src.routers import blog_analysis_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Create necessary directories
    dirs = [
        Path("analysis"),
        Path("analysis/keyword_research"),
        Path("reports")
    ]
    for dir_path in dirs:
        dir_path.mkdir(exist_ok=True, parents=True)
    
    yield

# Initialize FastAPI with lifespan
app = FastAPI(
    title="Blog Post Writer API",
    description="API for blog analysis and keyword research",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(blog_analysis_routes.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
