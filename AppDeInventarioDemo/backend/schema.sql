CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    sku TEXT NOT NULL COLLATE NOCASE UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    supplier TEXT NOT NULL DEFAULT '',
    cost INTEGER NOT NULL CHECK (cost BETWEEN 0 AND 1000000000),
    price INTEGER NOT NULL CHECK (price BETWEEN 0 AND 1000000000),
    opening_stock INTEGER NOT NULL DEFAULT 0 CHECK (opening_stock BETWEEN 0 AND 1000000),
    minimum INTEGER NOT NULL CHECK (minimum BETWEEN 0 AND 1000000),
    icon TEXT NOT NULL DEFAULT '◈',
    archived_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS movements (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
    type TEXT NOT NULL CHECK (type IN ('Compra', 'Venta', 'Ajuste')),
    delta INTEGER NOT NULL CHECK (delta BETWEEN -1000000 AND 1000000),
    unit_cost INTEGER NOT NULL CHECK (unit_cost BETWEEN 0 AND 1000000000),
    unit_price INTEGER NOT NULL CHECK (unit_price BETWEEN 0 AND 1000000000),
    date TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    request_id TEXT UNIQUE,
    request_hash TEXT,
    created_at TEXT NOT NULL,
    CHECK (
        (type = 'Compra' AND delta > 0) OR
        (type = 'Venta' AND delta < 0) OR
        (type = 'Ajuste' AND delta != 0)
    ),
    CHECK ((request_id IS NULL) = (request_hash IS NULL))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL CHECK (value BETWEEN 0 AND 1000000000)
);

CREATE INDEX IF NOT EXISTS idx_movements_item_date ON movements(item_id, date DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_type_date ON movements(type, date DESC);

CREATE TRIGGER IF NOT EXISTS prevent_negative_inventory
BEFORE INSERT ON movements
WHEN NEW.delta < 0
BEGIN
    SELECT CASE
        WHEN (
            SELECT i.opening_stock + COALESCE(SUM(m.delta), 0)
            FROM items AS i
            LEFT JOIN movements AS m ON m.item_id = i.id
            WHERE i.id = NEW.item_id
            GROUP BY i.id
        ) < -NEW.delta
        THEN RAISE(ABORT, 'insufficient_stock')
    END;
END;

CREATE TRIGGER IF NOT EXISTS prevent_movements_for_archived_item
BEFORE INSERT ON movements
WHEN EXISTS (SELECT 1 FROM items WHERE id = NEW.item_id AND archived_at IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'item_archived');
END;
