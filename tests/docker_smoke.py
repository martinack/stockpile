#!/usr/bin/env python3
"""Exercise the complete API through the frontend's Docker proxy."""

import json
import os
import sys
import ssl
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.getenv("STOCKPILE_SMOKE_URL", "https://localhost/api")


def request(path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, bytes, str]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    try:
        with urlopen(Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method), timeout=10, context=ssl._create_unverified_context()) as response:
            return response.status, response.read(), response.headers.get_content_type()
    except HTTPError as error:
        return error.code, error.read(), error.headers.get_content_type()


def json_request(path: str, method: str = "GET", payload: dict | None = None, expected: int = 200) -> dict | list:
    status, body, _ = request(path, method, payload)
    assert status == expected, f"{method} {path}: expected {expected}, got {status}: {body.decode()}"
    return json.loads(body)


def main() -> None:
    assert json_request("/health") == {"status": "ok"}

    run_id = uuid.uuid4().hex[:8]
    pantry_name, unit_name = f"Pantry-{run_id}", f"jars-{run_id}"
    pantry = json_request("/warehouses/", "POST", {"name": pantry_name, "location": "Kitchen"})
    jars = json_request("/units/", "POST", {"name": unit_name})
    assert json_request("/warehouses/", "POST", {"name": pantry_name}, expected=400)["detail"]
    assert json_request("/units/", "POST", {"name": unit_name}, expected=400)["detail"]
    assert json_request(f"/warehouses/{pantry['id']}")["name"] == pantry_name
    json_request(f"/warehouses/{pantry['id']}", "PATCH", {"location": "Shelf"})
    cellar = json_request("/warehouses/", "POST", {"name": "Cellar"})

    item = json_request(
        "/items/",
        "POST",
        {"name": "Tomato sauce", "quantity_value": 3, "unit_id": jars["id"], "warehouse_id": pantry["id"], "storage_date": "2027-01-01"},
    )
    search = json_request("/items/search/?q=tomato&unit_id=" + str(jars["id"]))
    assert search["items"][0]["id"] == item["id"]
    assert search["facets"]["warehouses"]["buckets"]
    assert search["facets"]["units"]["buckets"]
    assert search["facets"]["storage_date_min"].startswith("2027-01-01")
    assert json_request(f"/items/search/?unit_id={jars['id']}&storage_date_from=2028-01-01&storage_date_to=2027-01-01", expected=422)["detail"]

    status, qr_png, media_type = request(f"/qrcode/{item['code']}")
    assert status == 200 and media_type == "image/png" and qr_png.startswith(b"\x89PNG\r\n\x1a\n")

    json_request(f"/items/{item['code']}/move?{urlencode({'warehouse_id': cellar['id']})}", "POST")
    json_request(f"/items/{item['code']}/checkout", "POST")
    json_request(f"/items/{item['code']}", expected=404)
    json_request(f"/items/{item['id']}", "DELETE")
    request_status, _, _ = request(f"/qrcode/{item['code']}")
    assert request_status == 404

    json_request(f"/warehouses/{pantry['id']}", "DELETE")
    json_request(f"/warehouses/{cellar['id']}", "DELETE")
    assert json_request("/warehouses/") == []
    json_request(f"/units/{jars['id']}", "DELETE")
    assert json_request("/units/") == []
    print("Docker smoke test passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Docker smoke test failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
