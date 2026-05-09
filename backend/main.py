from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai, autofill, health, job_finder, jobs, market, packets, prediction, profile, resume, tracker
from app.core.config import settings
from app.db.database import init_db, seed_sample_jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_sample_jobs()
    yield


app = FastAPI(
    title="CareerAgent API",
    version="0.12.0",
    description="Stage 12 job finder and source discovery for a human-in-the-loop job search assistant.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(job_finder.router, prefix="/api/job-finder", tags=["job-finder"])
app.include_router(tracker.router, prefix="/api/tracker", tags=["tracker"])
app.include_router(packets.router, prefix="/api/packets", tags=["packets"])
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(prediction.router, prefix="/api/prediction", tags=["prediction"])
app.include_router(autofill.router, prefix="/api/autofill", tags=["autofill"])
