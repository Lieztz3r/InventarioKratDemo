"""Validated inventory operations and SQL-backed report queries."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .database import DEFAULT_ECONOMY, encode_request, new_id, open_database

MAX_QUANTITY = 1_000_000
MAX_AMOUNT = 1_000_000_000
ITEM_FIELDS = {
    "sku", "name", "category", "unit", "supplier",
    "cost", "price", "quantity", "minimum",
}
EDIT_FIELDS = {"sku", "name", "category", "unit", "supplier", "cost", "price", "minimum"}
SKU_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,23}$")


class InventoryError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _normalize_text(value: Any, field: str, maximum: int, required: bool = True) -> str:
    if not isinstance(value, str):
        raise InventoryError(400, "invalid_field", f"El campo {field} debe ser texto.")
    normalized = value.strip()
    if required and not normalized:
        raise InventoryError(400, "required_field", f"El campo {field} es obligatorio.")
    if len(normalized) > maximum:
        raise InventoryError(400, "field_too_long", f"El campo {field} supera {maximum} caracteres.")
    if any(ord(character) < 32 for character in normalized):
        raise InventoryError(400, "invalid_field", f"El campo {field} contiene caracteres de control.")
    return normalized


def _integer(value: Any, field: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InventoryError(400, "invalid_number", f"El campo {field} debe ser un número entero.")
    if value < 0 or value > maximum:
        raise InventoryError(400, "invalid_number", f"El campo {field} debe estar entre 0 y {maximum}.")
    return value


def _validate_item(data: object, editing: bool = False) -> dict[str, Any]:
    allowed = EDIT_FIELDS if editing else ITEM_FIELDS
    if not isinstance(data, dict):
        raise InventoryError(400, "invalid_body", "El cuerpo debe ser un objeto JSON.")
    unexpected = set(data) - allowed
    if unexpected:
        field = sorted(unexpected)[0]
        raise InventoryError(400, "unexpected_field", f"El campo {field} no está permitido.")
    required = allowed if editing else ITEM_FIELDS - {"supplier"}
    missing = required - set(data)
    if missing:
        raise InventoryError(400, "required_field", f"Falta el campo {sorted(missing)[0]}.")

    sku = _normalize_text(data.get("sku"), "SKU", 24).upper()
    if not SKU_PATTERN.fullmatch(sku):
        raise InventoryError(400, "invalid_sku", "Usa de 1 a 24 letras, números, puntos, guiones o guiones bajos.")

    result: dict[str, Any] = {
        "sku": sku,
        "name": _normalize_text(data.get("name"), "nombre", 70),
        "category": _normalize_text(data.get("category"), "categoría", 36),
        "unit": _normalize_text(data.get("unit"), "unidad", 18),
        "supplier": _normalize_text(data.get("supplier", ""), "proveedor", 50, required=False),
        "cost": _integer(data.get("cost"), "costo", MAX_AMOUNT),
        "price": _integer(data.get("price"), "precio", MAX_AMOUNT),
        "minimum": _integer(data.get("minimum"), "stock mínimo", MAX_QUANTITY),
    }
    if not editing:
        result["quantity"] = _integer(data.get("quantity"), "existencias iniciales", MAX_QUANTITY)
    return result


def _item_status(stock: int, minimum: int) -> str:
    if stock == 0:
        return "out"
    if stock <= minimum:
        return "low"
    return "normal"


def _searchable(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _inventory_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT i.id, i.sku, i.name, i.category, i.unit, i.supplier,
               i.cost, i.price, i.opening_stock, i.minimum, i.icon,
               i.archived_at, i.created_at, i.updated_at,
               i.opening_stock + COALESCE(SUM(m.delta), 0) AS stock
        FROM items AS i
        LEFT JOIN movements AS m ON m.item_id = i.id
        GROUP BY i.id
        ORDER BY i.name COLLATE NOCASE, i.id
        """
    ).fetchall()
    inventory: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        stock = int(item["stock"])
        item["margin"] = round((item["price"] - item["cost"]) * 100 / item["price"]) if item["price"] else 0
        item["inventory_value"] = stock * item["cost"]
        item["retail_value"] = stock * item["price"]
        item["archived"] = item["archived_at"] is not None
        item["status"] = "archived" if item["archived"] else _item_status(stock, item["minimum"])
        inventory.append(item)
    return inventory


def list_inventory(
    database_path: str,
    search: str = "",
    category: str = "",
    status: str = "",
    archive_state: str = "active",
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    if len(search) > 100:
        raise InventoryError(400, "invalid_search", "La búsqueda no puede superar 100 caracteres.")
    if len(category) > 36:
        raise InventoryError(400, "invalid_category", "La categoría no puede superar 36 caracteres.")
    if status and status not in {"attention", "normal", "low", "out"}:
        raise InventoryError(400, "invalid_status", "El estado debe ser attention, normal, low o out.")
    if archive_state not in {"active", "archived", "all"}:
        raise InventoryError(400, "invalid_archive_state", "El filtro de archivo debe ser active, archived o all.")
    if limit < 1 or limit > 200:
        raise InventoryError(400, "invalid_limit", "El límite debe estar entre 1 y 200.")
    if offset < 0 or offset > 1_000_000:
        raise InventoryError(400, "invalid_offset", "El desplazamiento debe ser un entero no negativo.")

    with open_database(database_path) as connection:
        all_items = _inventory_rows(connection)

    active_items = [item for item in all_items if not item["archived"]]
    categories = sorted({item["category"] for item in all_items}, key=str.casefold)
    filtered = (
        [item for item in all_items if item["archived"]]
        if archive_state == "archived"
        else active_items
    )
    if archive_state == "all":
        filtered = all_items
    normalized_search = _searchable(search.strip())
    if normalized_search:
        filtered = [
            item for item in filtered
            if normalized_search in _searchable(
                f'{item["name"]} {item["sku"]} {item["category"]} {item["supplier"]}'
            )
        ]
    if category:
        filtered = [item for item in filtered if item["category"] == category]
    if status == "attention":
        filtered = [item for item in filtered if item["status"] in {"low", "out"}]
    elif status:
        filtered = [item for item in filtered if item["status"] == status]
    summary = {
        "item_count": len(active_items),
        "archived_count": len(all_items) - len(active_items),
        "units": sum(item["stock"] for item in active_items),
        "stock_value": sum(item["inventory_value"] for item in active_items),
        "retail_value": sum(item["retail_value"] for item in active_items),
        "archived_units": sum(item["stock"] for item in all_items if item["archived"]),
        "archived_stock_value": sum(item["inventory_value"] for item in all_items if item["archived"]),
        "all_count": len(all_items),
        "all_units": sum(item["stock"] for item in all_items),
        "all_stock_value": sum(item["inventory_value"] for item in all_items),
        "low_stock": sum(item["status"] == "low" for item in active_items),
        "out_of_stock": sum(item["status"] == "out" for item in active_items),
    }
    page = filtered[offset:offset + limit]
    return {
        "items": page,
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(page) < len(filtered),
        "categories": categories,
        "summary": summary,
    }


def list_movements(
    database_path: str,
    movement_type: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    if movement_type and movement_type not in {"Compra", "Venta", "Ajuste"}:
        raise InventoryError(400, "invalid_movement_type", "El tipo debe ser Compra, Venta o Ajuste.")
    if limit < 1 or limit > 200:
        raise InventoryError(400, "invalid_limit", "El límite debe estar entre 1 y 200.")
    if offset < 0 or offset > 1_000_000:
        raise InventoryError(400, "invalid_offset", "El desplazamiento debe ser un entero no negativo.")

    with open_database(database_path) as connection:
        where = "WHERE m.type = ?" if movement_type else ""
        parameters: tuple[Any, ...] = (movement_type,) if movement_type else ()
        total = connection.execute(
            f"SELECT COUNT(*) FROM movements AS m {where}",
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT m.id, m.item_id, m.type, m.delta, m.unit_cost, m.unit_price,
                   m.date, m.note, m.created_at, m.request_id,
                   i.sku, i.name, i.category, i.unit, i.supplier
            FROM movements AS m
            JOIN items AS i ON i.id = m.item_id
            {where}
            ORDER BY m.date DESC, m.created_at DESC, m.id DESC
            LIMIT ? OFFSET ?
            """,
            parameters + (limit, offset),
        ).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(rows) < total,
    }


def _validate_date(value: object) -> str:
    if not isinstance(value, str):
        raise InventoryError(400, "invalid_date", "La fecha debe tener formato AAAA-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise InventoryError(400, "invalid_date", "La fecha no es válida; usa formato AAAA-MM-DD.") from error
    if parsed.isoformat() != value:
        raise InventoryError(400, "invalid_date", "La fecha debe tener formato AAAA-MM-DD.")
    if parsed > date.today():
        raise InventoryError(400, "future_date", "La fecha del movimiento no puede estar en el futuro.")
    return parsed.isoformat()


def create_item(database_path: str, data: object) -> tuple[dict[str, Any], list[str]]:
    item_data = _validate_item(data)
    item_id = new_id("itm")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with open_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                """
                INSERT INTO items (
                    id, sku, name, category, unit, supplier, cost, price,
                    opening_stock, minimum, icon, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, '◈', ?, ?)
                """,
                (
                    item_id, item_data["sku"], item_data["name"], item_data["category"],
                    item_data["unit"], item_data["supplier"], item_data["cost"],
                    item_data["price"], item_data["minimum"], now, now,
                ),
            )
            if item_data["quantity"]:
                connection.execute(
                    """
                    INSERT INTO movements (
                        id, item_id, type, delta, unit_cost, unit_price, date, note, created_at
                    ) VALUES (?, ?, 'Ajuste', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("mov"), item_id, item_data["quantity"],
                        item_data["cost"], item_data["price"], date.today().isoformat(),
                        "Saldo inicial al crear artículo", now,
                    ),
                )
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            if "sku" in str(error).casefold():
                raise InventoryError(409, "duplicate_sku", "Ese SKU ya existe en el catálogo.") from error
            raise
        except sqlite3.Error:
            connection.rollback()
            raise
    with open_database(database_path) as connection:
        result = next(item for item in _inventory_rows(connection) if item["id"] == item_id)
    return result, ["Saldo inicial registrado en el historial."] if item_data["quantity"] else []


def update_item(database_path: str, item_id: str, data: object) -> dict[str, Any]:
    item_data = _validate_item(data, editing=True)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with open_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.execute(
                """
                UPDATE items SET sku = ?, name = ?, category = ?, unit = ?,
                    supplier = ?, cost = ?, price = ?, minimum = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    item_data["sku"], item_data["name"], item_data["category"],
                    item_data["unit"], item_data["supplier"], item_data["cost"],
                    item_data["price"], item_data["minimum"], now, item_id,
                ),
            )
            if cursor.rowcount == 0:
                raise InventoryError(404, "item_not_found", "El artículo solicitado ya no existe.")
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            if "sku" in str(error).casefold():
                raise InventoryError(409, "duplicate_sku", "Ese SKU ya existe en el catálogo.") from error
            raise
        except (InventoryError, sqlite3.Error):
            connection.rollback()
            raise

    with open_database(database_path) as connection:
        item = next((item for item in _inventory_rows(connection) if item["id"] == item_id), None)
    if item is None:
        raise InventoryError(404, "item_not_found", "El artículo solicitado ya no existe.")
    return item


def set_item_archived(database_path: str, item_id: str, data: object) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != {"archived"} or not isinstance(data["archived"], bool):
        raise InventoryError(400, "invalid_archive_request", 'Envía únicamente {"archived": true o false}.')
    archived = data["archived"]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    archived_at = now if archived else None
    with open_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.execute(
                "UPDATE items SET archived_at = ?, updated_at = ? WHERE id = ?",
                (archived_at, now, item_id),
            )
            if cursor.rowcount == 0:
                raise InventoryError(404, "item_not_found", "El artículo solicitado ya no existe.")
            connection.commit()
        except (InventoryError, sqlite3.Error):
            connection.rollback()
            raise

    with open_database(database_path) as connection:
        result = next(item for item in _inventory_rows(connection) if item["id"] == item_id)
    return result


def create_movement(
    database_path: str,
    data: object,
    request_id: str | None = None,
) -> tuple[dict[str, Any], bool]:
    if not isinstance(data, dict):
        raise InventoryError(400, "invalid_body", "El cuerpo debe ser un objeto JSON.")
    allowed = {"item_id", "type", "quantity", "date", "note"}
    unexpected = set(data) - allowed
    if unexpected:
        raise InventoryError(400, "unexpected_field", f"El campo {sorted(unexpected)[0]} no está permitido.")
    missing = {"item_id", "type", "quantity", "date"} - set(data)
    if missing:
        raise InventoryError(400, "required_field", f"Falta el campo {sorted(missing)[0]}.")

    item_id = _normalize_text(data["item_id"], "artículo", 80)
    movement_type = data["type"]
    if not isinstance(movement_type, str) or movement_type not in {"Compra", "Venta", "Ajuste"}:
        raise InventoryError(400, "invalid_movement_type", "Selecciona una compra, venta o ajuste.")
    quantity = data["quantity"]
    if movement_type == "Ajuste":
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not -MAX_QUANTITY <= quantity <= MAX_QUANTITY:
            raise InventoryError(400, "invalid_quantity", "El ajuste debe ser un entero entre -1.000.000 y 1.000.000.")
        if quantity == 0:
            raise InventoryError(400, "invalid_quantity", "El ajuste debe ser distinto de cero.")
    else:
        quantity = _integer(quantity, "cantidad", MAX_QUANTITY)
        if quantity == 0:
            raise InventoryError(400, "invalid_quantity", "La cantidad debe ser mayor que cero.")
        if movement_type == "Venta":
            quantity = -quantity
    movement_date = _validate_date(data["date"])
    note = _normalize_text(data.get("note", ""), "detalle", 120, required=False)

    if request_id is not None and (not isinstance(request_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{8,80}", request_id)):
        raise InventoryError(400, "invalid_request_id", "El identificador de operación debe tener entre 8 y 80 caracteres.")
    fingerprint_data = {
        "date": movement_date,
        "item_id": item_id,
        "note": note,
        "quantity": quantity,
        "type": movement_type,
    }
    request_hash = hashlib.sha256(encode_request(fingerprint_data).encode("utf-8")).hexdigest()
    movement_id = new_id("mov")
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    with open_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            if request_id:
                previous = connection.execute(
                    "SELECT id, request_hash FROM movements WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if previous:
                    if previous["request_hash"] != request_hash:
                        raise InventoryError(
                            409,
                            "idempotency_conflict",
                            "El identificador de operación ya se usó con otros datos.",
                        )
                    connection.commit()
                    return get_movement(database_path, previous["id"]), True

            item = connection.execute(
                "SELECT cost, price, archived_at FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()
            if item is None:
                raise InventoryError(404, "item_not_found", "El artículo seleccionado no existe.")
            if item["archived_at"] is not None:
                raise InventoryError(409, "item_archived", "Reactiva el artículo antes de registrar un movimiento.")
            stock = connection.execute(
                """
                SELECT i.opening_stock + COALESCE(SUM(m.delta), 0)
                FROM items AS i
                LEFT JOIN movements AS m ON m.item_id = i.id
                WHERE i.id = ?
                GROUP BY i.id
                """,
                (item_id,),
            ).fetchone()[0]
            if stock + quantity < 0:
                raise InventoryError(
                    409,
                    "insufficient_stock",
                    f"Stock insuficiente: solo hay {stock} unidades disponibles.",
                )
            connection.execute(
                """
                INSERT INTO movements (
                    id, item_id, type, delta, unit_cost, unit_price, date, note,
                    request_id, request_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    movement_id, item_id, movement_type, quantity, item["cost"],
                    item["price"], movement_date, note, request_id,
                    request_hash if request_id else None, now,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            if "insufficient_stock" in str(error):
                raise InventoryError(409, "insufficient_stock", "No hay existencias suficientes para esa salida.") from error
            if request_id and "request_id" in str(error):
                existing = None
                with open_database(database_path) as retry:
                    existing = retry.execute(
                        "SELECT id, request_hash FROM movements WHERE request_id = ?",
                        (request_id,),
                    ).fetchone()
                if existing and existing["request_hash"] == request_hash:
                    return get_movement(database_path, existing["id"]), True
                raise InventoryError(409, "idempotency_conflict", "El identificador de operación ya se utilizó.") from error
            raise
        except InventoryError:
            connection.rollback()
            raise
        except sqlite3.Error:
            connection.rollback()
            raise
    return get_movement(database_path, movement_id), False


def get_movement(database_path: str, movement_id: str) -> dict[str, Any]:
    with open_database(database_path) as connection:
        movement = connection.execute(
            """
            SELECT m.id, m.item_id, m.type, m.delta, m.unit_cost, m.unit_price,
                   m.date, m.note, m.created_at, m.request_id,
                   i.sku, i.name, i.category, i.unit, i.supplier
            FROM movements AS m
            JOIN items AS i ON i.id = m.item_id
            WHERE m.id = ?
            """,
            (movement_id,),
        ).fetchone()
    if movement is None:
        raise InventoryError(404, "movement_not_found", "El movimiento solicitado no existe.")
    return dict(movement)


def dashboard(database_path: str) -> dict[str, Any]:
    today = date.today()
    month_start = (today - timedelta(days=29)).isoformat()
    first_month = today.replace(day=1)
    first_month_index = first_month.year * 12 + first_month.month - 1
    chart_months = []
    for month_index in range(first_month_index - 5, first_month_index + 1):
        year, zero_based_month = divmod(month_index, 12)
        chart_months.append(date(year, zero_based_month + 1, 1))
    six_month_start = chart_months[0].isoformat()
    with open_database(database_path) as connection:
        inventory = [item for item in _inventory_rows(connection) if not item["archived"]]
        sales = connection.execute(
            """
            SELECT COALESCE(SUM(ABS(delta) * unit_price), 0) AS revenue,
                   COALESCE(SUM(ABS(delta) * unit_cost), 0) AS cost,
                   COALESCE(SUM(ABS(delta)), 0) AS units
            FROM movements
            WHERE type = 'Venta' AND date >= ? AND date <= ?
            """,
            (month_start, today.isoformat()),
        ).fetchone()
        monthly = connection.execute(
            """
            SELECT substr(date, 1, 7) AS month,
                   SUM(ABS(delta) * unit_price) AS revenue
            FROM movements
            WHERE type = 'Venta' AND date >= ? AND date <= ?
            GROUP BY substr(date, 1, 7)
            """,
            (six_month_start, today.isoformat()),
        ).fetchall()
        movement_totals = connection.execute(
            """
            SELECT COUNT(*) AS movement_count,
                   COALESCE(SUM(CASE WHEN type = 'Compra' THEN delta ELSE 0 END), 0) AS purchased_units
            FROM movements
            """
        ).fetchone()

    spanish_months = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic")
    sales_by_month = {row["month"]: row["revenue"] for row in monthly}
    monthly_sales = [
        {
            "month": month.strftime("%Y-%m"),
            "label": spanish_months[month.month - 1],
            "revenue": sales_by_month.get(month.strftime("%Y-%m"), 0),
        }
        for month in chart_months
    ]
    revenue = int(sales["revenue"])
    gross_margin = round((revenue - int(sales["cost"])) * 100 / revenue) if revenue else 0
    alerts = [item for item in inventory if item["status"] in {"low", "out"}]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": "CLP",
        "sales_30d": {
            "revenue": revenue,
            "units": int(sales["units"]),
            "gross_margin": gross_margin,
        },
        "inventory": {
            "item_count": len(inventory),
            "units": sum(item["stock"] for item in inventory),
            "stock_value": sum(item["inventory_value"] for item in inventory),
            "retail_value": sum(item["retail_value"] for item in inventory),
            "low_stock": sum(item["status"] == "low" for item in inventory),
            "out_of_stock": sum(item["status"] == "out" for item in inventory),
            "health": round(sum(item["status"] == "normal" for item in inventory) * 100 / len(inventory)) if inventory else 0,
        },
        "sales_by_month": monthly_sales,
        "attention": alerts[:5],
        "movement_summary": {
            "total": movement_totals["movement_count"],
            "purchase_units": movement_totals["purchased_units"],
        },
    }


def get_economy(database_path: str) -> dict[str, int]:
    with open_database(database_path) as connection:
        rows = connection.execute("SELECT key, value FROM settings").fetchall()
    settings = dict(DEFAULT_ECONOMY)
    settings.update({row["key"]: row["value"] for row in rows})
    return settings


def update_economy(database_path: str, data: object) -> dict[str, int]:
    expected = set(DEFAULT_ECONOMY)
    if not isinstance(data, dict) or set(data) != expected:
        raise InventoryError(400, "invalid_settings", "Se requieren los cuatro supuestos económicos permitidos.")
    settings = {key: _integer(data[key], key, MAX_AMOUNT) for key in expected}
    with open_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                settings.items(),
            )
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
    return settings


def csv_rows(database_path: str) -> list[list[str | int]]:
    page = list_inventory(database_path, archive_state="active", limit=200)
    if page["summary"]["item_count"] > 200:
        raise InventoryError(409, "export_limit", "El catálogo supera el tamaño permitido para exportarlo de una sola vez.")
    rows: list[list[str | int]] = [
        [
            "SKU", "Artículo", "Categoría", "Proveedor", "Unidad",
            "Existencias", "Stock mínimo", "Costo unitario CLP",
            "Precio unitario CLP", "Valor de inventario CLP", "Margen bruto %",
            "Estado",
        ]
    ]
    labels = {"normal": "En nivel óptimo", "low": "Stock bajo", "out": "Agotado"}
    for item in page["items"]:
        rows.append(
            [
                item["sku"], item["name"], item["category"], item["supplier"],
                item["unit"], item["stock"], item["minimum"], item["cost"],
                item["price"], item["inventory_value"], item["margin"],
                labels[item["status"]],
            ]
        )
    return rows
