import psycopg
from psycopg.types.json import Json

from spam.config import settings

DDL = """ 
CREATE TABLE IF NOT EXISTS predictions (

    request_id uuid PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    model_version text,
    features json NOT NULL,
    score double precision,
    spam boolean,
    status_code integer NOT NULL DEFAULT 200,
    latency_ms real
)
"""

def init() -> None:
    if settings.database_url is None:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(DDL)
        conn.execute("Select pg_advisory_xact_lock(1)") # блокировка на время миграции


def save_prediction(
    request_id: str,
    features: dict,
    model_version: str | None = None,
    score: float | None = None,
    spam: bool | None = None,
    status_code: int = 200,
    latency_ms: float | None = None,
) -> None:
    if settings.database_url is None:
        return

    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO predictions
                (request_id, model_version, features, score, spam, status_code, latency_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request_id,
                model_version,
                Json(features),
                score,
                spam,
                status_code,
                latency_ms,
            ),
        )


#comment for pull request   
