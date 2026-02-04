from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.jobs import router as jobs_router
from app.api.matching import router as matching_router

app = FastAPI(title="InternNexus API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, tags=["jobs"])
app.include_router(matching_router, tags=["matching"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
