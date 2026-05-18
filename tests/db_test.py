# Smoke test full chain
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import ParsedRoom, HousePlanParsed, RABItem, RABResult
from src.db import save_project, save_floor_plan, save_budget_items

pid = save_project("Test Renov", "Malang, Jawa Timur")

denah = HousePlanParsed(rooms=[
    ParsedRoom(name="ruang tamu", length=4.0, width=4.0, confidence="high")
])
save_floor_plan(pid, denah)

rab = RABResult(
    project_name="Test Renov",
    location="Malang, Jawa Timur",
    items=[RABItem(room_name="ruang tamu", work_description="pasang keramik",
                   unit="m²", volume=16.0, unit_price=230000)],
)
save_budget_items(pid, rab)

# Cek isi DB
import sqlite3
conn = sqlite3.connect("data/rab.db")
print("Projects:", conn.execute("SELECT * FROM projects").fetchall())
print("Floor plans:", conn.execute("SELECT id, project_id, scale FROM floor_plans").fetchall())
print("Budget items:", conn.execute("SELECT room_name, work_description, subtotal FROM budget_items").fetchall())