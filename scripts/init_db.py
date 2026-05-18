"""Initialize SQLite database dengan apply semua migrations.

Run sekali saat setup project, atau setiap nambah migration baru.
Idempotent — aman di-run berulang karena semua DDL pakai IF NOT EXISTS.

Usage:
    uv run python scripts/init_db.py
"""
from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "rab.db"
MIGRATIONS_DIR = PROJECT_ROOT / "data" / "migrations"


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        logger.error("Migrations folder tidak ditemukan: %s", MIGRATIONS_DIR)
        return 1

    # Pastikan folder data/ ada (DB file akan dibuat di sini)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Sort file biar urutan eksekusi konsisten (001_, 002_, ...)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        logger.error("Tidak ada file .sql di %s", MIGRATIONS_DIR)
        return 1

    logger.info("Target DB: %s", DB_PATH)
    logger.info("Found %d migration file(s)", len(migration_files))

    conn = sqlite3.connect(DB_PATH)
    try:
        for mig in migration_files:
            logger.info("→ Applying: %s", mig.name)
            sql = mig.read_text(encoding="utf-8")
            conn.executescript(sql)
        conn.commit()
        logger.info("✅ Migrations selesai")
    except sqlite3.Error as e:
        logger.error("❌ Migration gagal: %s", e)
        conn.rollback()
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())