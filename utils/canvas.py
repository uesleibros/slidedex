import io
from PIL import Image

def compose_pokemon(sprite_bytes: bytes, background: Image.Image, size: tuple[int, int] = (200, 200), offset_y: int = 10) -> io.BytesIO:
    sprite_img = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
    sprite_img = sprite_img.resize(size, Image.Resampling.NEAREST)

    composed = background.copy()
    position = ((composed.width - sprite_img.width) // 2, composed.height - sprite_img.height - offset_y)
    composed.paste(sprite_img, position, sprite_img)

    buffer = io.BytesIO()
    composed.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
