from fastapi.testclient import TestClient

from tests.conftest import override_generate_reply


def test_agent_test_route(client: TestClient) -> None:
    with override_generate_reply("Howdy!"):
        r = client.post("/test/agent", json={"message": "Hello"})
    assert r.status_code == 200
    assert r.json()["reply"] == "Howdy!"

