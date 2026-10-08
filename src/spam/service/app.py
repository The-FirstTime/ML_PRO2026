import time
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from spam import db
from spam.model_store import load_model


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
    pipeline, meta, version = load_model()
    app.state.pipeline = pipeline
    app.state.meta = meta
    app.state.version = version

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
        status_code=200,
        latency_ms=latency_ms,
    )
    spam = score >= app.state.meta["threshold"]

    return Prediction(score=score, spam=spam, model_version=app.state.version, request_id=request_id, latency_ms=latency_ms)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        body = {}

    if not isinstance(body, dict):
        body = {"body": body}

    request_id = str(uuid.uuid4())

    db.save_prediction(
        request_id=request_id,
        features=body,
        status_code=422,
    )

    return JSONResponse(
        status_code=422,
        content={
            "request_id": request_id,
            "detail": exc.errors(),
        },
    )

