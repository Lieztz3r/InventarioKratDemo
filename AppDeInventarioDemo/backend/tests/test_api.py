from __future__ import annotations

import csv
import http.client
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.database import DEFAULT_ECONOMY, initialize_database
from backend.server import AtlasRequestHandler, LocalhostServer


class InventoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="atlas-inventory-tests-")
        self.database = Path(self.directory.name) / "test.sqlite3"
        initialize_database(self.database)
        self.server = LocalhostServer(("127.0.0.1", 0), AtlasRequestHandler, self.database)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.origin = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.directory.cleanup()

    def request(
        self,
        method: str,
        path: str,
        body: object | None = None,
        *,
        headers: dict[str, str] | None = None,
        encode_json: bool = True,
    ) -> tuple[int, http.client.HTTPMessage, bytes, object | None]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        request_headers = dict(headers or {})
        payload = None
        if body is not None:
            if encode_json:
                payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json")
            else:
                payload = body if isinstance(body, bytes) else str(body).encode("utf-8")
            request_headers.setdefault("Origin", self.origin)
        connection.request(method, path, body=payload, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        response_headers = response.headers
        content_type = response_headers.get("Content-Type", "")
        if "application/json" in content_type:
            decoded = json.loads(raw.decode("utf-8"))
        else:
            decoded = None
        connection.close()
        return status, response_headers, raw, decoded

    @staticmethod
    def new_item(**overrides: object) -> dict[str, object]:
        item: dict[str, object] = {
            "sku": "QA-010",
            "name": "Artículo de prueba",
            "category": "Pruebas",
            "unit": "unidad",
            "supplier": "Proveedor test",
            "cost": 1000,
            "price": 2000,
            "quantity": 10,
            "minimum": 2,
        }
        item.update(overrides)
        return item

    def test_health_and_seeded_dashboard_are_consistent(self) -> None:
        status, headers, _, health = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["database"], "connected")
        self.assertEqual(health["schema_version"], 1)
        self.assertEqual(health["items"], 10)
        self.assertTrue(headers.get("X-Request-ID"))

        status, _, _, dashboard = self.request("GET", "/api/dashboard")
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["inventory"]["item_count"], 10)
        self.assertEqual(len(dashboard["sales_by_month"]), 6)
        self.assertEqual(dashboard["movement_summary"]["total"], 19)
        self.assertEqual(dashboard["inventory"]["low_stock"], 1)
        self.assertEqual(dashboard["sales_30d"]["revenue"], 525500)

    def test_catalog_supports_filtering_pagination_and_archive(self) -> None:
        status, _, _, data = self.request("GET", "/api/inventory?search=cafe&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["sku"], "CAF-001")

        status, _, _, created = self.request("POST", "/api/items", self.new_item())
        self.assertEqual(status, 201)
        item = created["item"]
        self.assertEqual(item["stock"], 10)
        self.assertEqual(item["status"], "normal")
        self.assertEqual(created["notes"], ["Saldo inicial registrado en el historial."])

        status, _, _, movements = self.request("GET", "/api/movements?type=Ajuste&limit=100")
        opening = next(m for m in movements["items"] if m["item_id"] == item["id"])
        self.assertEqual(opening["delta"], 10)
        self.assertEqual(opening["note"], "Saldo inicial al crear artículo")

        status, _, _, archived = self.request(
            "PATCH",
            f'/api/items/{item["id"]}/archive',
            {"archived": True},
        )
        self.assertEqual(status, 200)
        self.assertTrue(archived["item"]["archived"])
        self.assertEqual(archived["item"]["stock"], 10)

        status, _, _, active = self.request("GET", "/api/inventory")
        self.assertEqual(status, 200)
        self.assertNotIn(item["id"], {row["id"] for row in active["items"]})
        self.assertEqual(active["summary"]["archived_count"], 1)

        status, _, _, history = self.request("GET", "/api/inventory?archive=archived")
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in history["items"]], [item["id"]])

        status, _, _, moved = self.request(
            "POST",
            "/api/movements",
            {"item_id": item["id"], "type": "Compra", "quantity": 3, "date": "2026-10-01"},
        )
        self.assertEqual(status, 409)
        self.assertEqual(moved["error"]["code"], "item_archived")

        status, _, _, restored = self.request(
            "PATCH",
            f'/api/items/{item["id"]}/archive',
            {"archived": False},
        )
        self.assertEqual(status, 200)
        self.assertFalse(restored["item"]["archived"])

    def test_validation_rejects_duplicate_skus_unsafe_quantities_and_future_dates(self) -> None:
        status, _, _, created = self.request("POST", "/api/items", self.new_item())
        self.assertEqual(status, 201)
        status, _, _, duplicate = self.request(
            "POST",
            "/api/items",
            self.new_item(sku="qa-010", name="SKU duplicado"),
        )
        self.assertEqual(status, 409)
        self.assertEqual(duplicate["error"]["code"], "duplicate_sku")

        status, _, _, invalid = self.request(
            "POST",
            "/api/movements",
            {"item_id": created["item"]["id"], "type": "Venta", "quantity": 11, "date": "2026-10-01"},
        )
        self.assertEqual(status, 409)
        self.assertEqual(invalid["error"]["code"], "insufficient_stock")

        status, _, _, zero_adjustment = self.request(
            "POST",
            "/api/movements",
            {"item_id": created["item"]["id"], "type": "Ajuste", "quantity": 0, "date": "2026-10-01"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(zero_adjustment["error"]["code"], "invalid_quantity")

        status, _, _, future = self.request(
            "POST",
            "/api/movements",
            {"item_id": created["item"]["id"], "type": "Compra", "quantity": 1, "date": "2999-01-01"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(future["error"]["code"], "future_date")

        status, _, _, unknown = self.request("POST", "/api/items", self.new_item(extra_field="ignored"))
        self.assertEqual(status, 400)
        self.assertEqual(unknown["error"]["code"], "unexpected_field")

    def test_sale_creation_is_atomic_and_idempotent(self) -> None:
        _, _, _, created = self.request("POST", "/api/items", self.new_item(quantity=10))
        item_id = created["item"]["id"]
        movement = {
            "item_id": item_id,
            "type": "Venta",
            "quantity": 3,
            "date": "2026-10-01",
            "note": "Venta de prueba",
        }
        key = "sales-request-id-001"
        status, headers, _, created_movement = self.request(
            "POST",
            "/api/movements",
            movement,
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(status, 201)
        self.assertEqual(headers["Idempotent-Replay"], "false")
        self.assertEqual(created_movement["movement"]["unit_price"], 2000)

        status, headers, _, repeated = self.request(
            "POST",
            "/api/movements",
            movement,
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Idempotent-Replay"], "true")
        self.assertEqual(repeated["movement"]["id"], created_movement["movement"]["id"])

        status, _, _, conflict = self.request(
            "POST",
            "/api/movements",
            {**movement, "quantity": 2},
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(status, 409)
        self.assertEqual(conflict["error"]["code"], "idempotency_conflict")

        _, _, _, catalog = self.request("GET", "/api/inventory?search=QA-010")
        self.assertEqual(catalog["items"][0]["stock"], 7)
        _, _, _, movement_page = self.request("GET", "/api/movements?type=Venta")
        sale_row = next(row for row in movement_page["items"] if row["item_id"] == item_id)
        self.assertEqual(sale_row["unit_price"], 2000)

    def test_concurrent_sales_cannot_overdraw_stock(self) -> None:
        _, _, _, created = self.request("POST", "/api/items", self.new_item(quantity=10))
        item_id = created["item"]["id"]
        barrier = threading.Barrier(2)

        def sell(index: int) -> int:
            barrier.wait(timeout=5)
            status, _, _, _ = self.request(
                "POST",
                "/api/movements",
                {
                    "item_id": item_id,
                    "type": "Venta",
                    "quantity": 7,
                    "date": "2026-10-01",
                    "note": f"Concurrent sale {index}",
                },
                headers={"Idempotency-Key": f"parallel-sale-000{index}"},
            )
            return status

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(sell, (1, 2)))
        self.assertEqual(sorted(results), [201, 409])
        _, _, _, catalog = self.request("GET", "/api/inventory?search=QA-010")
        self.assertEqual(catalog["items"][0]["stock"], 3)

    def test_catalog_edits_keep_historical_movement_prices(self) -> None:
        _, _, _, created = self.request("POST", "/api/items", self.new_item())
        item = created["item"]
        _, _, _, updated = self.request(
            "PUT",
            f'/api/items/{item["id"]}',
            {
                "sku": "QA-010",
                "name": "Artículo actualizado",
                "category": "Pruebas",
                "unit": "unidad",
                "supplier": "Nuevo proveedor",
                "cost": 1500,
                "price": 3000,
                "minimum": 4,
            },
        )
        self.assertEqual(updated["item"]["stock"], 10)
        self.assertEqual(updated["item"]["price"], 3000)

        _, _, _, sales = self.request(
            "POST",
            "/api/movements",
            {"item_id": item["id"], "type": "Venta", "quantity": 1, "date": "2026-10-01"},
        )
        self.assertEqual(sales["movement"]["unit_price"], 3000)
        _, _, _, movements = self.request("GET", "/api/movements?type=Ajuste")
        initial_stock = next(row for row in movements["items"] if row["item_id"] == item["id"])
        self.assertEqual(initial_stock["unit_cost"], 1000)
        self.assertEqual(initial_stock["unit_price"], 2000)

    def test_economy_settings_persist_and_validate(self) -> None:
        changed = {"price": 49900, "fixed": 3100000, "variable": 6500, "investment": 27000000}
        status, _, _, saved = self.request("PUT", "/api/settings/economy", changed)
        self.assertEqual(status, 200)
        self.assertEqual(saved, changed)

        initialize_database(self.database)
        status, _, _, loaded = self.request("GET", "/api/settings/economy")
        self.assertEqual(status, 200)
        self.assertEqual(loaded, changed)

        status, _, _, rejected = self.request("PUT", "/api/settings/economy", {**changed, "admin": 1})
        self.assertEqual(status, 400)
        self.assertEqual(rejected["error"]["code"], "invalid_settings")

    def test_api_defends_localhost_origin_body_size_and_query_contracts(self) -> None:
        _, _, _, created = self.request("POST", "/api/items", self.new_item())
        self.assertEqual(created["item"]["sku"], "QA-010")

        status, _, _, wrong_origin = self.request(
            "POST",
            "/api/items",
            self.new_item(sku="QA-011"),
            headers={"Origin": "https://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(wrong_origin["error"]["code"], "invalid_origin")

        status, _, _, bad_query = self.request("GET", "/api/inventory?unexpected=1")
        self.assertEqual(status, 400)
        self.assertEqual(bad_query["error"]["code"], "unexpected_query_parameter")

        status, _, _, unsupported = self.request(
            "POST",
            "/api/items",
            b'{"sku":"QA-011"}',
            headers={"Content-Type": "text/plain", "Origin": self.origin},
            encode_json=False,
        )
        self.assertEqual(status, 415)
        self.assertEqual(unsupported["error"]["code"], "unsupported_media_type")

        status, _, _, oversized = self.request(
            "POST",
            "/api/items",
            b" " * 32769,
            headers={
                "Content-Type": "application/json",
                "Content-Length": "32769",
                "Origin": self.origin,
            },
            encode_json=False,
        )
        self.assertEqual(status, 413)
        self.assertEqual(oversized["error"]["code"], "request_too_large")

        status, _, _, malformed = self.request(
            "POST",
            "/api/items",
            b"{",
            headers={"Content-Type": "application/json", "Origin": self.origin},
            encode_json=False,
        )
        self.assertEqual(status, 400)
        self.assertEqual(malformed["error"]["code"], "invalid_json")

        status, _, _, unknown = self.request("GET", "/api/not-a-route")
        self.assertEqual(status, 404)
        self.assertEqual(unknown["error"]["code"], "endpoint_not_found")

    def test_spreadsheet_export_escapes_formula_cells_and_includes_utf8(self) -> None:
        _, _, _, _ = self.request(
            "POST",
            "/api/items",
            self.new_item(name="=HYPERLINK(\"https://example.invalid\")", sku="QA-011"),
        )
        status, headers, raw, _ = self.request("GET", "/api/inventory/export")
        self.assertEqual(status, 200)
        self.assertEqual(raw[:3], b"\xef\xbb\xbf")
        self.assertIn("attachment", headers["Content-Disposition"])
        rows = list(csv.reader(io.StringIO(raw[3:].decode("utf-8"))))
        exported = next(row for row in rows if row[0] == "QA-011")
        self.assertTrue(exported[1].startswith("'="))
        self.assertEqual(exported[2], "Pruebas")

    def test_demo_reset_requires_explicit_confirmation_and_restores_seed(self) -> None:
        self.request("POST", "/api/items", self.new_item())
        status, _, _, missing_confirmation = self.request("POST", "/api/demo/reset", {})
        self.assertEqual(status, 400)
        self.assertEqual(missing_confirmation["error"]["code"], "confirmation_required")

        status, _, _, result = self.request("POST", "/api/demo/reset", {"confirm": True})
        self.assertEqual(status, 200)
        self.assertTrue(result["reset"])
        self.assertEqual(result["economy"], DEFAULT_ECONOMY)

        _, _, _, dashboard = self.request("GET", "/api/dashboard")
        self.assertEqual(dashboard["inventory"]["item_count"], 10)
        self.assertEqual(dashboard["movement_summary"]["total"], 19)

    def test_static_routes_are_same_origin_safe_and_have_security_headers(self) -> None:
        status, headers, content, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Atlas", content)
        self.assertIn("Content-Security-Policy", headers)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

        status, headers, content, _ = self.request("GET", "/favicon.svg")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", content)

        status, _, content, _ = self.request("GET", "/INVESTIGACION_PROYECTOS.md")
        self.assertEqual(status, 200)
        self.assertIn(b"81/81", content)

        status, headers, content, _ = self.request("GET", "/backend/database.py")
        self.assertEqual(status, 404)
        self.assertNotIn(b"seed_demo", content)

        status, _, _, denied = self.request(
            "GET",
            "/api/health",
            headers={"Host": "evil.example"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(denied["error"]["code"], "invalid_host")


if __name__ == "__main__":
    unittest.main()
