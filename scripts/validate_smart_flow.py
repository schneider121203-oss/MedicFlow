"""Validate the simulator launch, one-time exchange and FHIR context."""

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from backend.main import app


def main() -> None:
    client = TestClient(app)
    context_response = client.get("/simulator/api/context")
    assert context_response.status_code == 200
    context = context_response.json()
    patient = context["patients"][0]
    appointments = [item for item in context["appointments"] if item["patient_id"] == patient["id"]]
    launch_response = client.post(
        "/simulator/api/launch",
        json={
            "patient_id": patient["id"],
            "appointment_id": appointments[0]["id"] if appointments else None,
        },
    )
    assert launch_response.status_code == 200
    launch_url = launch_response.json()["launch_url"]
    code = parse_qs(urlparse(launch_url).query)["launch"][0]

    exchange = client.post("/api/smart/exchange", json={"code": code})
    assert exchange.status_code == 200
    token = exchange.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.get(f"/simulator/fhir/Patient/{patient['id']}", headers=headers).status_code == 200
    )
    assert client.get("/api/organization/me", headers=headers).status_code == 200
    assert client.post("/api/smart/exchange", json={"code": code}).status_code == 400
    print("SMART/FHIR simulator checks passed")


if __name__ == "__main__":
    main()
