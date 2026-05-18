import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.models import ParsedRoom
from src.services.rab import generate_rab

rooms = [
    ParsedRoom(name="kamar tidur", length=4.0, width=4.0, confidence="high", notes="bangun ruangan baru dari awal"),
    ParsedRoom(name="dapur", length=2.0, width=2.5, confidence="high", notes="bangun ruangan baru dari awal"),
]

result = generate_rab(rooms, lokasi="Malang, Jawa Timur", project_name="Test Renov")
print(f"Total items: {len(result.items)}")
print(f"Total RAB: Rp {result.total:,.0f}")
for item in result.items:
    print(f"  - {item.room_name}: {item.work_description} = Rp {item.subtotal:,.0f}")