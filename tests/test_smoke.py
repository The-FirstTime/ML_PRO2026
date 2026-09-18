def test_predict_smoke(client, good_row):
    r = client.post("/v1/predict", json=good_row)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["score"] <= 1.0
    assert isinstance(body["spam"], bool)
    assert body["latency_ms"] >= 0
    assert body["model_version"]
    assert body["request_id"]


def test_predict_recognizes_obvious_spam(client, spam_row):
    r = client.post("/v1/predict", json=spam_row)
    assert r.status_code == 200
    body = r.json()
    assert body["spam"] is True
    assert body["score"] >= 0.5


def test_predict_recognizes_obvious_ham(client, good_row):
    r = client.post("/v1/predict", json=good_row)
    body = r.json()
    assert body["spam"] is False
    assert body["score"] < 0.5


def test_single_and_repeat_agree(client, good_row):
    s1 = client.post("/v1/predict", json=good_row).json()["score"]
    s2 = client.post("/v1/predict", json=good_row).json()["score"]
    assert abs(s1 - s2) < 1e-12
