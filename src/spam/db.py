import psycopg 
from psycopg.types.json import Json

from spam.config import settings
DDL = """ 
CREATE TABLE IF NOT EXISTS predictions (

    request_id uuid PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    model_version text NOT NULL,
    features json NOT NULL,
    score double precision NOT NULL,
    spam boolean NOT NULL,
    latency_ms real
)
"""

def init() -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(DDL)


def save_prediction(
    request_id: str,
    model_version: str,
    features: dict,
    score: float,
    spam: bool,
    latency_ms: float | None = None,
) -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO predictions (request_id, model_version, features, score, spam, latency_ms)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                request_id,
                model_version,
                Json(features),
                score,
                spam,
                latency_ms,
            ),
        )
