from src.services.vision import compress_image

with open("denah1.jpeg", "rb") as f:
    original = f.read()

compressed = compress_image(original, max_size=1024)

with open("compressed_test.jpg", "wb") as f:
    f.write(compressed)

print(f"Original:   {len(original):>10} bytes")
print(f"Compressed: {len(compressed):>10} bytes")
print(f"Saved to: compressed_test.jpg")
