import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agent, batch, profiles, scores
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gail — Adaptive Behavioral Profiling Agent",
    description="A system that builds living behavioral profiles and powers an adaptive conversational agent.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(profiles.router)
app.include_router(scores.router)
app.include_router(agent.router)
app.include_router(batch.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "gail"}


@app.on_event("startup")
async def startup():
    logger.info("Gail starting up...")
    # Optionally initialize database tables
    try:
        from src.database import init_db
        await init_db()
        logger.info("Database tables ensured")
    except Exception as e:
        logger.warning("Could not auto-create tables (run migrations instead): %s", e)


def run():
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
