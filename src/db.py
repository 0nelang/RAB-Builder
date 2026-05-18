"""SQLite database operations.

Single source of truth untuk koneksi DB + CRUD operations.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from src.models import HousePlanParsed, RABResult

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "rab.db"


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager SQLite — auto commit/rollback, selalu close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_project(name: str, location: str) -> int:
    """Insert project baru. Returns project_id."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (name, location, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (name, location),
        )
        project_id = cursor.lastrowid

    logger.info("Project saved → id=%d | '%s'", project_id, name)
    return project_id  # type: ignore[return-value]


def save_floor_plan(project_id: int, result: HousePlanParsed) -> None:
    """Simpan hasil parsing denah ke tabel floor_plans."""
    rooms_json = json.dumps(
        [r.model_dump() for r in result.rooms],
        ensure_ascii=False,
    )
    warnings_json = json.dumps(result.warnings, ensure_ascii=False)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO floor_plans (project_id, rooms_json, scale, warnings_json, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (project_id, rooms_json, result.scale, warnings_json),
        )

    logger.info(
        "Floor plan saved → project_id=%d | %d rooms",
        project_id, len(result.rooms),
    )


def save_budget_items(project_id: int, result: RABResult) -> None:
    """Bulk insert RAB items ke tabel budget_items.

    Field RABItem 1:1 dengan kolom budget_items, jadi mapping straightforward.
    """
    rows = [
        (
            project_id,
            item.room_name,
            item.work_description,
            item.unit,
            item.volume,
            item.unit_price,
            item.subtotal,
        )
        for item in result.items
    ]

    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO budget_items
                (project_id, room_name, work_description, unit, volume,
                 unit_price, subtotal, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            rows,
        )

    logger.info(
        "Budget items saved → project_id=%d | %d items | total=Rp %,.0f",
        project_id, len(result.items), result.total,
    )