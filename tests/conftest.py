import pytest
from fastapi.testclient import TestClient

from spam.service.app import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def good_row():
    return {
        "text": "Hey, just checking if we're still on for coffee tomorrow at 10am?",
    }


@pytest.fixture()
def spam_row():
    return {
        "text": "WINNER!! You have been selected to receive a free $1000 prize, call now!",
    }
