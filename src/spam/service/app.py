import time
import uuid

from contextlib import asynccontextmanager

import joblib
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from spam.config import settings
from spam import db


class Features(BaseModel):
    model_config = {"extra": "forbid"}

    text: str = Field(min_length=1)


class Prediction(BaseModel):
    score: float
    spam: bool
    model_version: str
    request_id: str
    latency_ms: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = joblib.load(settings.model_path)
    app.state.pipeline = bundle["pipeline"]
    app.state.meta = bundle["metadata"]
    app.state.version = bundle["metadata"]["version"]

    db.init()
    yield
    app.state.pipeline = None


app = FastAPI(title="spam-service", version="1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model_version": getattr(app.state, "version", "unknown")}


@app.get("/ready")
def ready():
    if getattr(app.state, "pipeline", None) is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return {"status": "ready"}


@app.post("/v1/predict")
def predict(x: Features, bg: BackgroundTasks) -> Prediction:
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())
    payload = x.model_dump()

    score = float(app.state.pipeline.predict_proba([payload["text"]])[0, 1])

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    bg.add_task(
    db.save_prediction,
    request_id=request_id,
    model_version=app.state.version,
    features=payload,
    score=score,
    spam=score >= app.state.meta["threshold"],
    latency_ms=latency_ms,
)
    spam = score >= app.state.meta["threshold"]

    return Prediction(score=score, spam=spam, model_version=app.state.version, request_id=request_id, latency_ms=latency_ms)