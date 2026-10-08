from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.backup import backup_database
from backend.database import DEFAULT_ECONOMY, initialize_database, open_database


class DatabaseIntegrityTests(unittest.TestCase):
    def test_database_checks_inventory_ledger_and_schema_version(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-db-tests-") as directory:
            database = Path(directory) / "atlas.sqlite3"
            initialize_database(database)
            with open_database(database) as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0], 4)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM movements").fetchone()[0], 19)
                for item in connection.execute(
                    """
                    SELECT i.opening_stock + COALESCE(SUM(m.delta), 0) AS stock
                    FROM items AS i
                    LEFT JOIN movements AS m ON m.item_id = i.id
                    GROUP BY i.id
                    """
                ):
                    self.assertGreaterEqual(item["stock"], 0)

            initialize_database(database)
            with open_database(database) as connection:
                settings = dict(connection.execute("SELECT key, value FROM settings").fetchall())
                self.assertEqual(settings, DEFAULT_ECONOMY)

    def test_database_trigger_independently_prevents_overselling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-db-trigger-tests-") as directory:
            database = Path(directory) / "atlas.sqlite3"
            initialize_database(database)
            with open_database(database) as connection:
                with self.assertRaisesRegex(sqlite3.IntegrityError, "insufficient_stock"):
                    connection.execute(
                        """
                        INSERT INTO movements (
                            id, item_id, type, delta, unit_cost, unit_price,
                            date, note, created_at
                        ) VALUES (
                            'mov-trigger-test', 'itm-010', 'Venta', -1000, 18900,
                            32900, '2026-10-01', 'must fail', '2026-10-01T00:00:00+00:00'
                        )
                        """
                    )

    def test_database_schema_version_and_foreign_keys_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-db-version-tests-") as directory:
            database = Path(directory) / "atlas.sqlite3"
            initialize_database(database)
            with open_database(database) as connection:
                with self.assertRaisesRegex(sqlite3.IntegrityError, "FOREIGN KEY"):
                    connection.execute(
                        """
                        INSERT INTO movements (
                            id, item_id, type, delta, unit_cost, unit_price,
                            date, note, created_at
                        ) VALUES (
                            'mov-orphan-test', 'itm-missing', 'Compra', 1, 1,
                            2, '2026-10-01', 'must fail', '2026-10-01T00:00:00+00:00'
                        )
                        """
                    )
                connection.execute("PRAGMA user_version = 999")
            with self.assertRaisesRegex(RuntimeError, "newer than supported"):
                initialize_database(database)

    def test_online_backup_is_complete_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-backup-tests-") as directory:
            source = Path(directory) / "active.sqlite3"
            target = Path(directory) / "backup" / "snapshot.sqlite3"
            initialize_database(source)

            self.assertEqual(backup_database(source, target), target.resolve())
            with open_database(target) as connection:
                self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM movements").fetchone()[0], 19)

            with self.assertRaisesRegex(FileExistsError, "already exists|ya existe"):
                backup_database(source, target)
            with self.assertRaisesRegex(ValueError, "distinta"):
                backup_database(source, source)
