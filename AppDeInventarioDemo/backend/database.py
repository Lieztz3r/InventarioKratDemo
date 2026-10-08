"""SQLite initialization and deterministic demo data."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1
DEFAULT_ECONOMY = {
    "price": 39900,
    "fixed": 2400000,
    "variable": 5500,
    "investment": 23330000,
}

DEMO_ITEMS = (
    ("CAF-001", "Café en grano · origen Colombia", "Insumos", "kg", "Tostaduría Cordillera", 8900, 14900, 88, 24, "◉"),
    ("ENV-014", "Vaso compostable 12 oz", "Empaques", "unid.", "EcoPack Chile", 145, 390, 1000, 300, "◌"),
    ("FIL-006", "Filtro de papel tamaño 02", "Insumos", "caja", "Distribuidora Nativa", 4200, 7400, 36, 12, "▤"),
    ("LIM-003", "Detergente concentrado 5 L", "Limpieza", "bidón", "Suministros Sur", 6800, 11900, 30, 10, "⌂"),
    ("SEG-008", "Guantes nitrilo talla M", "Seguridad", "caja", "Suministros Sur", 3900, 6900, 18, 12, "⊞"),
    ("TAZ-021", "Taza cerámica 300 ml", "Menaje", "unid.", "Cerámica del Valle", 2950, 5900, 60, 18, "◍"),
    ("ETQ-004", "Etiqueta térmica 50 × 30 mm", "Empaques", "rollo", "Impresos Centro", 1750, 3200, 40, 10, "▨"),
    ("LIM-011", "Sanitizante de superficie 1 L", "Limpieza", "botella", "Suministros Sur", 2450, 4400, 24, 8, "◈"),
    ("ENV-019", "Bolsa papel kraft mediana", "Empaques", "paquete", "EcoPack Chile", 2650, 4900, 100, 30, "▱"),
    ("ACC-002", "Báscula digital de precisión", "Equipamiento", "unid.", "Equipamiento Andes", 18900, 32900, 8, 3, "⊞"),
)

# Offsets preserve the original demo's sales, purchases, and six-month chart.
DEMO_MOVEMENTS = (
    ("Venta", "CAF-001", -8, 2, "Venta mostrador"),
    ("Venta", "ENV-014", -180, 2, "Consumo cafetería"),
    ("Venta", "FIL-006", -4, 4, "Reposición de barra"),
    ("Venta", "SEG-008", -8, 5, "Consumo interno"),
    ("Compra", "CAF-001", 20, 7, "Factura demo #1038"),
    ("Compra", "ENV-014", 300, 9, "Reposición semanal"),
    ("Venta", "TAZ-021", -15, 12, "Venta tienda"),
    ("Venta", "ENV-019", -20, 15, "Venta mostrador"),
    ("Venta", "ETQ-004", -12, 18, "Uso en etiquetado"),
    ("Venta", "LIM-011", -6, 23, "Consumo de limpieza"),
    ("Compra", "LIM-003", 6, 27, "Factura demo #1019"),
    ("Venta", "CAF-001", -10, 35, "Venta mostrador"),
    ("Venta", "ENV-014", -220, 42, "Consumo cafetería"),
    ("Compra", "TAZ-021", 20, 57, "Reposición de menaje"),
    ("Venta", "FIL-006", -5, 71, "Reposición de barra"),
    ("Venta", "ENV-019", -18, 94, "Venta mostrador"),
    ("Compra", "CAF-001", 15, 119, "Compra de temporada"),
    ("Venta", "ENV-014", -160, 143, "Consumo cafetería"),
    ("Venta", "TAZ-021", -11, 161, "Venta tienda"),
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def open_database(path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    else:
        if connection.in_transaction:
            connection.commit()
    finally:
        connection.close()


def seed_demo(connection: sqlite3.Connection) -> None:
    now = utc_timestamp()
    item_ids: dict[str, str] = {}
    item_values: dict[str, tuple[int, int]] = {}
    for index, item in enumerate(DEMO_ITEMS, start=1):
        sku, name, category, unit, supplier, cost, price, opening, minimum, icon = item
        item_id = f"itm-{index:03}"
        item_ids[sku] = item_id
        item_values[sku] = (cost, price)
        connection.execute(
            """
            INSERT INTO items (
                id, sku, name, category, unit, supplier, cost, price,
                opening_stock, minimum, icon, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id, sku, name, category, unit, supplier, cost, price,
                opening, minimum, icon, now, now,
            ),
        )

    today = date.today()
    for index, (movement_type, sku, delta, days_ago, note) in enumerate(DEMO_MOVEMENTS, start=1):
        cost, price = item_values[sku]
        movement_date = (today - timedelta(days=days_ago)).isoformat()
        connection.execute(
            """
            INSERT INTO movements (
                id, item_id, type, delta, unit_cost, unit_price, date, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"mov-{index:03}", item_ids[sku], movement_type, delta,
                cost, price, movement_date, note, now,
            ),
        )

    connection.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        DEFAULT_ECONOMY.items(),
    )


def initialize_database(path: str | Path) -> None:
    database_path = Path(path).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")

    with open_database(database_path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than supported version {SCHEMA_VERSION}."
            )
        if version == 0:
            script = (
                "BEGIN IMMEDIATE;\n"
                f"{schema}\n"
                f"PRAGMA user_version = {SCHEMA_VERSION};\n"
                "COMMIT;"
            )
            try:
                connection.executescript(script)
            except sqlite3.Error:
                if connection.in_transaction:
                    connection.rollback()
                raise

        item_count = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        if item_count == 0:
            connection.execute("BEGIN IMMEDIATE")
            try:
                seed_demo(connection)
                connection.commit()
            except sqlite3.Error:
                connection.rollback()
                raise

        result = connection.execute("PRAGMA quick_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"Database integrity check failed: {result}")


def reset_demo(path: str | Path) -> None:
    with open_database(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM movements")
            connection.execute("DELETE FROM items")
            connection.execute("DELETE FROM settings")
            seed_demo(connection)
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
    initialize_database(path)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def encode_request(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
