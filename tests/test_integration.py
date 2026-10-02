import os

import psycopg
import pytest

DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="нужен Postgres: задайте DATABASE_URL"),
]


def test_prediction_is_logged(client, good_row):
    body = client.post("/v1/predict", json=good_row).json()

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, features->>'Contract' "
            "FROM predictions WHERE request_id = %s",
            (body["request_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == body["model_version"]
    assert row[1] == pytest.approx(body["score"])
    assert row[2] == good_row["text"]


def test_garbage_request_logs_422(client: TestClient):
    response = client.post(
        "/v1/predict",
        json={"hacker_field": "invalid payload"},
    )

    assert response.status_code == 422
    request_id = response.json()["request_id"]

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            SELECT status_code, model_version, score, spam
            FROM predictions
            WHERE request_id = %s
            """,
            (request_id,),
        ).fetchone()

    assert row == (422, None, None, None)
    assert row[2] == good_row["Contract"]
