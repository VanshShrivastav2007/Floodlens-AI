"""
Nepal Terai Flood Intelligence System - FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .api.endpoints import router as api_router

app = FastAPI(
    title="Nepal Terai Flood Intelligence System",
    description="Rapid Flood Extent Mapping and Settlement Impact Assessment for the Nepal Terai (Problem Statement 01)",
    version="1.0.0"
)

# Enable CORS for frontend Vite dev server and production clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs directory for GeoTIFF and GeoJSON downloads
outputs_dir = os.path.abspath("outputs")
os.makedirs(outputs_dir, exist_ok=True)
os.makedirs(os.path.join(outputs_dir, "rasters"), exist_ok=True)
os.makedirs(os.path.join(outputs_dir, "vectors"), exist_ok=True)
os.makedirs(os.path.join(outputs_dir, "reports"), exist_ok=True)

app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "title": "Nepal Terai Flood Intelligence System",
        "objective": "Problem Statement 01: Rapid Flood Extent Mapping and Settlement Impact Assessment for Nepal Terai",
        "api_docs": "/docs",
        "status": "RUNNING"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
