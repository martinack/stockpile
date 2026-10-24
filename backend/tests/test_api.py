from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stockpile.main import Settings, create_app


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'storage.db'}",
        qrcodes_dir=tmp_path / "qrcodes",
        solr_url=None,
        create_schema=True,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client, settings


def create_unit(client: TestClient, name: str = "jars") -> dict:
    response = client.post("/units/", json={"name": name})
    assert response.status_code == 200
    return response.json()


def create_warehouse(client: TestClient, name: str = "Pantry") -> dict:
    response = client.post("/warehouses/", json={"name": name, "location": "Kitchen"})
    assert response.status_code == 200
    return response.json()


def test_health_and_warehouse_lifecycle(client) -> None:
    api, _ = client
    assert api.get("/health").json() == {"status": "ok"}

    warehouse = create_warehouse(api)
    assert api.post("/warehouses/", json={"name": "Pantry"}).status_code == 400
    assert api.get("/warehouses/").json() == [warehouse]

    updated = api.patch(
        f"/warehouses/{warehouse['id']}",
        json={"name": "Cool pantry", "location": "Basement", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Cool pantry"
    assert api.get("/warehouses/?active_only=false").json()[0]["is_active"] is False


def test_item_lifecycle_and_qrcode(client) -> None:
    api, settings = client
    warehouse = create_warehouse(api)
    unit = create_unit(api)

    assert api.post("/items/", json={"name": "Missing", "quantity_value": 1, "unit_id": unit["id"], "warehouse_id": 999}).status_code == 404
    created = api.post(
        "/items/",
        json={"name": "Tomato sauce", "quantity_value": 3, "unit_id": unit["id"], "warehouse_id": warehouse["id"], "storage_date": "2027-01-01"},
    )
    assert created.status_code == 200
    item = created.json()
    qr_path = settings.qrcodes_dir / f"{item['code']}.png"
    assert qr_path.exists()

    qr_response = api.get(f"/qrcode/{item['code']}")
    assert qr_response.headers["content-type"] == "image/png"
    assert qr_response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert float(api.get(f"/items/{item['code']}").json()["quantity_value"]) == 3

    assert api.post(f"/items/{item['code']}/move").json()["warehouse_id"] is None
    assert api.post(f"/items/{item['code']}/move?warehouse_id={warehouse['id']}").status_code == 200
    assert api.post(f"/items/{item['code']}/checkout").status_code == 200
    assert api.get(f"/items/{item['code']}").status_code == 404

    assert api.delete(f"/items/{item['id']}").status_code == 200
    assert not qr_path.exists()


def test_deleting_warehouse_detaches_items(client) -> None:
    api, _ = client
    warehouse = create_warehouse(api)
    unit = create_unit(api)
    item = api.post("/items/", json={"name": "Flour", "quantity_value": 1, "unit_id": unit["id"], "warehouse_id": warehouse["id"]}).json()

    assert api.delete(f"/warehouses/{warehouse['id']}").status_code == 200
    assert api.get(f"/items/{item['code']}").json()["warehouse_id"] is None


def test_unit_lifecycle_and_item_validation(client) -> None:
    api, _ = client
    unit = create_unit(api, "bottles")
    assert api.post("/units/", json={"name": "bottles"}).status_code == 400
    assert api.patch(f"/units/{unit['id']}", json={"name": "Bottle"}).json()["name"] == "Bottle"

    # The new contract accepts only positive numeric quantities and active units.
    assert api.post("/items/", json={"name": "Water", "quantity_value": 0, "unit_id": unit["id"]}).status_code == 422
    assert api.delete(f"/units/{unit['id']}").status_code == 200
    assert api.get("/units/?active_only=false").json()[0]["is_active"] is False
    assert api.post("/items/", json={"name": "Water", "quantity_value": 1, "unit_id": unit["id"]}).status_code == 404
