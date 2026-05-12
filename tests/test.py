import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.services.vision import compress_image

from src.services.vision import hause_plan_result, img_to_base64_url, _load_prompt, _call_vision_model, _parse_response


# with open("tests/denah1.jpeg", "rb") as f:
#     img = f.read()

# url = img_to_base64_url(compress_image(img))
# prompt = _load_prompt()

# raw = _call_vision_model(url, prompt, temp=0.0)

# print("--- Raw AI reply ---")
# print(_parse_response(raw))
# print("--- End ---")
print('correct')
with open("tests/denah1.jpeg", "rb") as f:
    img = f.read()

result = hause_plan_result(img)

print(f"Rooms found: {len(result.rooms)}")
for room in result.rooms:
    print(f"  - {room}")
print(f"Warnings: {result.warning}")