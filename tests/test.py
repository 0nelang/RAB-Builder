import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.services.vision import compress_image

from src.services.vision import hause_plan_result

print('correct')
with open("tests/denah1.jpeg", "rb") as f:
    img = f.read()

result = hause_plan_result(img)

print(f"Rooms found: {len(result.rooms)}")
for room in result.rooms:
    print(f"  - {room}")
print(f"Warnings: {result.warning}")