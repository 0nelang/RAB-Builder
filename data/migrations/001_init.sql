-- Schema awal RAB Builder.
-- Idempotent: aman di-run berulang.

PRAGMA foreign_keys = ON;

-- ============================================================
-- projects: 1 baris per proyek RAB
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    location    TEXT    NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- floor_plans: hasil parsing AI dari foto denah (1:1 ke project)
-- ============================================================
CREATE TABLE IF NOT EXISTS floor_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    rooms_json      TEXT    NOT NULL,            -- JSON array of ParsedRoom
    scale           TEXT,                        -- nullable
    warnings_json   TEXT    NOT NULL DEFAULT '[]',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_floor_plans_project_id
    ON floor_plans(project_id);

-- ============================================================
-- budget_items: item-item RAB (banyak per proyek)
-- Maps ke Pydantic RABItem
-- ============================================================
CREATE TABLE IF NOT EXISTS budget_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id        INTEGER NOT NULL,
    room_name         TEXT    NOT NULL,
    work_description  TEXT    NOT NULL,
    unit              TEXT    NOT NULL,
    volume            REAL    NOT NULL,
    unit_price        REAL    NOT NULL,
    subtotal          REAL    NOT NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_budget_items_project_id
    ON budget_items(project_id);