"""Create consistent SQLite backups while the local server is running."""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .database import open_database

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = Path(
    os.environ.get("ATLAS_DATABASE", str(APP_ROOT / "backend" / "data" / "inventory.sqlite3"))
)


def backup_database(source_path: str | Path, destination_path: str | Path) -> Path:
    source = Path(source_path).resolve()
    destination = Path(destination_path).resolve()
    if source == destination:
        raise ValueError("La copia debe guardarse en una ruta distinta de la base de datos activa.")
    if destination.exists():
        raise FileExistsError(f"La copia de destino ya existe: {destination}")
    if not source.is_file():
        raise FileNotFoundError(f"No existe la base de datos: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb"):
        pass
    try:
        with open_database(source) as connection:
            copy = sqlite3.connect(str(destination))
            try:
                connection.backup(copy)
                result = copy.execute("PRAGMA quick_check").fetchone()[0]
                if result != "ok":
                    raise sqlite3.DatabaseError(f"La copia no superó la verificación: {result}")
            finally:
                copy.close()
    except (OSError, sqlite3.Error):
        if destination.exists():
            destination.unlink()
        raise
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea una copia coherente de la base de datos SQLite de Atlas.")
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Ruta de la base SQLite activa (por defecto, ATLAS_DATABASE o la ruta local estándar).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Ruta de destino. Por defecto se crea un archivo con fecha en backups\\.",
    )
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = args.output or APP_ROOT / "backups" / f"inventory-{stamp}.sqlite3"
    try:
        result = backup_database(args.database, destination)
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Copia de seguridad creada: {result}")


if __name__ == "__main__":
    main()
