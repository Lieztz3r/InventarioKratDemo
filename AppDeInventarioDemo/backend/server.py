"""Same-origin localhost HTTP API and static web server."""

from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import json
import logging
import os
import re
import socket
import sqlite3
import uuid
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import inventory
from .database import DEFAULT_ECONOMY, initialize_database, open_database, reset_demo

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 32 * 1024
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/README.md": ("README.md", "text/markdown; charset=utf-8"),
    "/INFORME_ECONOMICO.md": ("INFORME_ECONOMICO.md", "text/markdown; charset=utf-8"),
    "/INVESTIGACION_PROYECTOS.md": ("INVESTIGACION_PROYECTOS.md", "text/markdown; charset=utf-8"),
}
SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    (
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    ),
)


class LocalhostServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 32

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        database_path: Path,
    ) -> None:
        self.address_family = socket.AF_INET6 if ":" in address[0] else socket.AF_INET
        super().__init__(address, handler)
        self.database_path = database_path


class AtlasRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: LocalhostServer

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_OPTIONS(self) -> None:
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {
                "error": {
                    "code": "method_not_allowed",
                    "message": "La aplicación solo acepta solicitudes del mismo origen.",
                }
            },
            extra_headers=(("Allow", "GET, HEAD, POST, PUT, PATCH"),),
        )

    def do_DELETE(self) -> None:
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def do_TRACE(self) -> None:
        self._method_not_allowed()

    def _method_not_allowed(self) -> None:
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {
                "error": {
                    "code": "method_not_allowed",
                    "message": "Ese método HTTP no está habilitado.",
                }
            },
            extra_headers=(("Allow", "GET, HEAD, POST, PUT, PATCH"),),
        )

    def _dispatch(self, method: str) -> None:
        request_id = str(uuid.uuid4())
        try:
            if not self._valid_host():
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": {"code": "invalid_host", "message": "La aplicación solo acepta solicitudes a localhost."}},
                    request_id=request_id,
                )
                return
            if method in {"POST", "PUT", "PATCH"} and not self._valid_origin():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"error": {"code": "invalid_origin", "message": "La solicitud no proviene de esta aplicación local."}},
                    request_id=request_id,
                )
                return

            parsed = urlsplit(self.path)
            if parsed.fragment or parsed.username or parsed.password:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": {"code": "invalid_url", "message": "La URL solicitada no es válida."}},
                    request_id=request_id,
                )
                return
            if parsed.path.startswith("/api/"):
                body = self._read_json_body() if method in {"POST", "PUT", "PATCH"} else None
                status, response, headers = self._route_api(method, parsed.path, parsed.query, body)
                self._send_json(status, response, extra_headers=headers, request_id=request_id)
                return
            if method in {"GET", "HEAD"}:
                self._serve_static(method, parsed.path, request_id)
                return
            self._method_not_allowed()
        except inventory.InventoryError as error:
            self._send_json(
                error.status,
                {"error": {"code": error.code, "message": error.message}},
                request_id=request_id,
            )
        except (sqlite3.Error, OSError):
            logging.exception("Database or filesystem error while handling a request.")
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": {
                        "code": "storage_error",
                        "message": "No se pudo completar la operación de almacenamiento.",
                    }
                },
                request_id=request_id,
            )
        except Exception:
            logging.exception("Unexpected application error.")
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "Ocurrió un error interno; consulta el registro local del servidor.",
                    }
                },
                request_id=request_id,
            )

    def _valid_host(self) -> bool:
        host_values = self.headers.get_all("Host", [])
        if len(host_values) != 1:
            return False
        try:
            parsed = urlsplit(f"http://{host_values[0]}")
            if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                return False
            hostname = parsed.hostname
            if hostname is None or parsed.port not in {None, self.server.server_port}:
                return False
            if hostname.casefold() == "localhost":
                return True
            return ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            return False

    def _valid_origin(self) -> bool:
        if self.headers.get("Sec-Fetch-Site", "").casefold() == "cross-site":
            return False
        origins = self.headers.get_all("Origin", [])
        if not origins:
            return True
        if len(origins) != 1 or origins[0] == "null":
            return False
        parsed = urlsplit(origins[0])
        if parsed.scheme != "http" or parsed.path or parsed.query or parsed.fragment:
            return False
        try:
            if parsed.port != self.server.server_port or parsed.username or parsed.password:
                return False
            hostname = parsed.hostname
            return bool(
                hostname
                and (
                    hostname.casefold() == "localhost"
                    or ipaddress.ip_address(hostname).is_loopback
                )
            )
        except ValueError:
            return False

    def _read_json_body(self) -> object:
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            raise inventory.InventoryError(411, "content_length_required", "Envía un cuerpo JSON con longitud explícita.")
        content_length = int(lengths[0])
        if content_length > MAX_BODY_BYTES:
            raise inventory.InventoryError(413, "request_too_large", "El cuerpo supera el máximo de 32 KiB.")
        if self.headers.get("Transfer-Encoding"):
            raise inventory.InventoryError(400, "transfer_encoding_not_supported", "Las solicitudes codificadas en fragmentos no están habilitadas.")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
        if content_type != "application/json":
            raise inventory.InventoryError(415, "unsupported_media_type", "El contenido debe ser application/json.")
        payload = self.rfile.read(content_length)
        if len(payload) != content_length:
            raise inventory.InventoryError(400, "incomplete_body", "El cuerpo de la solicitud está incompleto.")
        try:
            return json.loads(payload.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise inventory.InventoryError(400, "invalid_json", "El cuerpo no contiene JSON UTF-8 válido.") from error

    def _query(self, query: str) -> dict[str, str]:
        parsed = parse_qs(query, keep_blank_values=True, strict_parsing=False)
        if any(len(values) != 1 for values in parsed.values()):
            raise inventory.InventoryError(400, "duplicate_query_parameter", "No repitas los parámetros de la URL.")
        return {key: values[0] for key, values in parsed.items()}

    def _integer_query(
        self,
        query: dict[str, str],
        key: str,
        default: int,
        maximum: int,
    ) -> int:
        raw = query.get(key)
        if raw is None:
            return default
        if not raw.isascii() or not raw.isdecimal():
            raise inventory.InventoryError(400, "invalid_query_parameter", f"El parámetro {key} debe ser un entero.")
        value = int(raw)
        if value > maximum:
            raise inventory.InventoryError(
                400,
                "invalid_query_parameter",
                f"El parámetro {key} no puede superar {maximum}.",
            )
        return value

    def _require_query_keys(self, query: dict[str, str], allowed: set[str]) -> None:
        unexpected = set(query) - allowed
        if unexpected:
            field = sorted(unexpected)[0]
            raise inventory.InventoryError(
                400,
                "unexpected_query_parameter",
                f"El parámetro {field} no está permitido para este recurso.",
            )

    def _route_api(
        self,
        method: str,
        path: str,
        raw_query: str,
        body: object,
    ) -> tuple[int, object, tuple[tuple[str, str], ...]]:
        query = self._query(raw_query)
        if method == "GET" and path == "/api/health":
            self._require_query_keys(query, set())
            return HTTPStatus.OK, self._health(), ()
        if method == "GET" and path == "/api/dashboard":
            self._require_query_keys(query, set())
            return HTTPStatus.OK, inventory.dashboard(str(self.server.database_path)), ()
        if method == "GET" and path == "/api/settings/economy":
            self._require_query_keys(query, set())
            return HTTPStatus.OK, inventory.get_economy(str(self.server.database_path)), ()
        if method == "PUT" and path == "/api/settings/economy":
            self._require_query_keys(query, set())
            return HTTPStatus.OK, inventory.update_economy(str(self.server.database_path), body), ()
        if method == "GET" and path == "/api/inventory":
            self._require_query_keys(query, {"search", "category", "status", "archive", "limit", "offset"})
            result = inventory.list_inventory(
                str(self.server.database_path),
                search=query.get("search", ""),
                category=query.get("category", ""),
                status=query.get("status", ""),
                archive_state=query.get("archive", "active"),
                limit=self._integer_query(query, "limit", 200, 200),
                offset=self._integer_query(query, "offset", 0, 1_000_000),
            )
            return HTTPStatus.OK, result, ()
        if method == "GET" and path == "/api/inventory/export":
            self._require_query_keys(query, set())
            return HTTPStatus.OK, self._inventory_csv(), (
                ("Content-Disposition", "attachment; filename=krateroi-inventario.csv"),
            )
        if method == "GET" and path == "/api/movements":
            self._require_query_keys(query, {"type", "limit", "offset"})
            return HTTPStatus.OK, inventory.list_movements(
                str(self.server.database_path),
                movement_type=query.get("type", ""),
                limit=self._integer_query(query, "limit", 100, 200),
                offset=self._integer_query(query, "offset", 0, 1_000_000),
            ), ()
        if method == "POST" and path == "/api/items":
            self._require_query_keys(query, set())
            item, notes = inventory.create_item(str(self.server.database_path), body)
            return HTTPStatus.CREATED, {"item": item, "notes": notes}, ()
        item_match = re_match_item(path)
        if method == "PUT" and item_match is not None:
            self._require_query_keys(query, set())
            item = inventory.update_item(str(self.server.database_path), item_match, body)
            return HTTPStatus.OK, {"item": item}, ()
        archive_match = re_match_archive(path)
        if method == "PATCH" and archive_match is not None:
            self._require_query_keys(query, set())
            result = inventory.set_item_archived(
                str(self.server.database_path),
                archive_match,
                body,
            )
            return HTTPStatus.OK, {"item": result}, ()
        if method == "POST" and path == "/api/movements":
            self._require_query_keys(query, set())
            request_values = self.headers.get_all("Idempotency-Key", [])
            if len(request_values) > 1:
                raise inventory.InventoryError(400, "invalid_request_id", "Envía un solo encabezado Idempotency-Key.")
            movement, replayed = inventory.create_movement(
                str(self.server.database_path),
                body,
                request_values[0] if request_values else None,
            )
            return (
                HTTPStatus.OK if replayed else HTTPStatus.CREATED,
                {"movement": movement, "replayed": replayed},
                (("Idempotent-Replay", "true" if replayed else "false"),),
            )
        if method == "POST" and path == "/api/demo/reset":
            self._require_query_keys(query, set())
            if body != {"confirm": True}:
                raise inventory.InventoryError(
                    400,
                    "confirmation_required",
                    "Confirma el restablecimiento con {\"confirm\": true}.",
                )
            reset_demo(self.server.database_path)
            return HTTPStatus.OK, {"reset": True, "economy": DEFAULT_ECONOMY}, ()
        if path == "/api" or path.startswith("/api/"):
            raise inventory.InventoryError(404, "endpoint_not_found", "No existe esa ruta de la API.")
        raise inventory.InventoryError(404, "endpoint_not_found", "No existe esa ruta de la API.")

    def _health(self) -> dict[str, object]:
        with open_database(self.server.database_path) as connection:
            item_count = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            checks = connection.execute("PRAGMA quick_check").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        if checks != "ok":
            raise sqlite3.DatabaseError(f"Database integrity check failed: {checks}")
        return {"status": "ok", "database": "connected", "schema_version": version, "items": item_count}

    def _inventory_csv(self) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output, dialect="excel", lineterminator="\r\n")
        for row in inventory.csv_rows(str(self.server.database_path)):
            writer.writerow([self._spreadsheet_value(value) for value in row])
        return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")

    @staticmethod
    def _spreadsheet_value(value: str | int) -> str | int:
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + value
        return value

    def _serve_static(self, method: str, request_path: str, request_id: str) -> None:
        static_entry = STATIC_FILES.get(unquote(request_path))
        if static_entry is None:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": {"code": "not_found", "message": "No se encontró el recurso solicitado."}},
                request_id=request_id,
            )
            return
        filename, content_type = static_entry
        file_path = ROOT / filename
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._write_common_headers(request_id)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(body)

    def _send_json(
        self,
        status: int,
        payload: object,
        extra_headers: tuple[tuple[str, str], ...] = (),
        request_id: str | None = None,
    ) -> None:
        if isinstance(payload, bytes):
            body = payload
            content_type = "text/csv; charset=utf-8"
        else:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        self.send_response(status)
        self._write_common_headers(request_id)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _write_common_headers(self, request_id: str | None) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        if request_id:
            self.send_header("X-Request-ID", request_id)

    def log_message(self, format_string: str, *args: object) -> None:
        status = args[1] if len(args) > 1 else ""
        path = urlsplit(self.path).path
        logging.info("%s %s %s", self.command, path, status)


def re_match_item(path: str) -> str | None:
    prefix = "/api/items/"
    if not path.startswith(prefix):
        return None
    item_id = path[len(prefix):]
    if not item_id or "/" in item_id or len(item_id) > 80:
        return None
    return item_id


def re_match_archive(path: str) -> str | None:
    prefix = "/api/items/"
    suffix = "/archive"
    if not path.startswith(prefix) or not path.endswith(suffix):
        return None
    item_id = path[len(prefix):-len(suffix)]
    if not item_id or "/" in item_id or len(item_id) > 80:
        return None
    return item_id


def parse_args() -> argparse.Namespace:
    default_data = ROOT / "backend" / "data"
    parser = argparse.ArgumentParser(description="Servidor local de Atlas · Inventario Krateroi.")
    parser.add_argument("--host", default="127.0.0.1", help="Interfaz loopback donde escuchar (por defecto: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=int(os.environ.get("ATLAS_PORT", "8765")), help="Puerto HTTP (por defecto: 8765).")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.environ.get("ATLAS_DATABASE", str(default_data / "inventory.sqlite3"))),
        help="Ruta opcional del archivo SQLite persistente.",
    )
    args = parser.parse_args()
    try:
        if not ipaddress.ip_address(args.host).is_loopback:
            parser.error("solo se permite enlazar una dirección loopback por seguridad; Atlas demo no incluye autenticación.")
    except ValueError:
        parser.error("--host debe ser una dirección IP loopback, por ejemplo 127.0.0.1 o ::1.")
    if not 1 <= args.port <= 65535:
        parser.error("--port debe estar entre 1 y 65535.")
    return args


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = parse_args()
    database_path = args.database.resolve()
    initialize_database(database_path)
    httpd = LocalhostServer(
        (args.host, args.port),
        partial(AtlasRequestHandler),
        database_path,
    )
    actual_host, actual_port = httpd.server_address[:2]
    logging.info("Atlas escuchando en http://%s:%s/", actual_host, actual_port)
    logging.info("Base de datos SQLite: %s", database_path)
    logging.info("Detén el servicio con Ctrl+C. El servidor se limita a este equipo (loopback).")
    try:
        httpd.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        logging.info("Cerrando el servidor.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
