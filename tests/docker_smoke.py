#!/usr/bin/env python3
"""Exercise the complete API through the frontend's Docker proxy."""

import json
import os
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.getenv("STOCKPILE_SMOKE_URL", "http://localhost:8080/api")


def request(path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, bytes, str]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    try:
        with urlopen(Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method), timeout=10) as response:
            return response.status, response.read(), response.headers.get_content_type()
    except HTTPError as error:
        return error.code, error.read(), error.headers.get_content_type()


def json_request(path: str, method: str = "GET", payload: dict | None = None, expected: int = 200) -> dict | list:
    status, body, _ = request(path, method, payload)
    assert status == expected, f"{method} {path}: expected {expected}, got {status}: {body.decode()}"
    return json.loads(body)


def main() -> None:
    assert json_request("/health") == {"status": "ok"}

    pantry = json_request("/warehouses/", "POST", {"name": "Pantry", "location": "Kitchen"})
    assert json_request("/warehouses/", "POST", {"name": "Pantry"}, expected=400)["detail"]
    assert json_request(f"/warehouses/{pantry['id']}")["name"] == "Pantry"
    json_request(f"/warehouses/{pantry['id']}", "PATCH", {"location": "Shelf"})
    cellar = json_request("/warehouses/", "POST", {"name": "Cellar"})

    item = json_request(
        "/items/",
        "POST",
        {"name": "Tomato sauce", "quantity": "3 jars", "warehouse_id": pantry["id"]},
    )
    assert json_request("/items/?search=tomato")[0]["id"] == item["id"]
    assert json_request(f"/warehouses/{pantry['id']}/items")[0]["id"] == item["id"]

    status, qr_png, media_type = request(f"/qrcode/{item['code']}")
    assert status == 200 and media_type == "image/png" and qr_png.startswith(b"\x89PNG\r\n\x1a\n")

    json_request(f"/items/{item['code']}/move?{urlencode({'warehouse_id': cellar['id']})}", "POST")
    assert json_request(f"/warehouses/{cellar['id']}/items")[0]["id"] == item["id"]
    json_request(f"/items/{item['code']}/checkout", "POST")
    json_request(f"/items/{item['code']}", expected=404)
    json_request(f"/items/{item['id']}", "DELETE")
    request_status, _, _ = request(f"/qrcode/{item['code']}")
    assert request_status == 404

    json_request(f"/warehouses/{pantry['id']}", "DELETE")
    json_request(f"/warehouses/{cellar['id']}", "DELETE")
    assert json_request("/warehouses/") == []
    print("Docker smoke test passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Docker smoke test failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
