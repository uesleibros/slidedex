import io
import asyncio
from typing import List, Tuple
from PIL import Image, ImageOps
import numpy as np

PROFILE_COORDS: List[Tuple[int, int, int, int]] = [
    (5, -8, 137, 83),
    (150, -8, 137, 83),
    (290, -8, 137, 83),
    (5, 71, 137, 83),
    (150, 71, 137, 83),
    (290, 71, 137, 83),
]

def _to_box(sprite_bytes: bytes, box: int) -> Image.Image:
    im = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
    im = ImageOps.contain(im, (box, box), method=Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    x = (box - im.width) // 2
    y = box - im.height
    canvas.paste(im, (x, y), im)
    im.close()
    return canvas

def _process_sprite_crop(
    sprite_bytes: bytes,
    w: int,
    h: int,
    crop: bool = True,
    scale_boost: float = 1.0,
    max_height_ratio: float = 1.0,
    force_height: bool = False,
    max_width_ratio: float = 1.0,
    pad: int = 2,
) -> Image.Image:
    im = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
    
    bbox = im.getbbox()
    if bbox:
        l, t, r, b = bbox
        l = max(0, l - pad)
        t = max(0, t - pad)
        r = min(im.width, r + pad)
        b = min(im.height, b + pad)
        im = im.crop((l, t, r, b))

    if crop:
        cw, ch = im.size
        crop_h = int(ch / 1.6)
        im = im.crop((0, 0, cw, crop_h))

    if force_height:
        sf = (h / im.height) * scale_boost
    else:
        sf = min(w / im.width, h / im.height) * scale_boost

    nw, nh = int(im.width * sf), int(im.height * sf)

    if nh > int(h * max_height_ratio):
        ratio = (h * max_height_ratio) / nh
        nw = max(1, int(nw * ratio))
        nh = max(1, int(nh * ratio))

    if nw > int(w * max_width_ratio):
        ratio = (w * max_width_ratio) / nw
        nw = max(1, int(nw * ratio))
        nh = max(1, int(nh * ratio))

    res = im.resize((nw, nh), Image.Resampling.NEAREST)
    im.close()
    
    final = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = (w - nw) // 2
    y = h - nh
    final.paste(res, (x, y), res)
    res.close()
    return final

def _compose_pokemon(
    sprite_bytes: bytes,
    background: Image.Image,
    box_size: int = 130,
    ground_y: int = 180,
    scale_boost: float = 1.0
) -> io.BytesIO:
    spr = _process_sprite_crop(
        sprite_bytes,
        box_size,
        box_size,
        crop=False,
        scale_boost=scale_boost,
        max_height_ratio=0.95,
        force_height=False,
        max_width_ratio=0.95,
        pad=4,
    )
    
    composed = background.copy()
    x = (composed.width - spr.width) // 2
    y = ground_y - spr.height
    composed.paste(spr, (x, y), spr)
    spr.close()
    
    buf = io.BytesIO()
    composed.save(buf, format="PNG", optimize=False, compress_level=0)
    composed.close()
    buf.seek(0)
    return buf

def _compose_battle(
    player_bytes: bytes,
    enemy_bytes: bytes,
    background: Image.Image,
    box_size: int = 140,
    player_ground_y: int = 250,
    enemy_ground_y: int = 140,
    player_x: int = 40,
    enemy_x: int = 280
) -> io.BytesIO:
    composed = background.copy()
    
    if player_bytes:
        p = _process_sprite_crop(
            player_bytes,
            int(box_size * 1.2),
            int(box_size * 1.2),
            crop=False,
            scale_boost=1.15,
            max_height_ratio=0.95,
            force_height=True,
            max_width_ratio=0.95,
            pad=2,
        )
        composed.paste(p, (player_x, player_ground_y - p.height), p)
        p.close()
        
    if enemy_bytes:
        e = _process_sprite_crop(
            enemy_bytes,
            int(box_size),
            int(box_size),
            crop=False,
            scale_boost=1.0,
            max_height_ratio=0.75,
            force_height=True,
            max_width_ratio=0.85,
            pad=2,
        )
        composed.paste(e, (enemy_x, enemy_ground_y - e.height), e)
        e.close()
        
    buf = io.BytesIO()
    composed.save(buf, format="PNG", optimize=False, compress_level=0)
    composed.close()
    buf.seek(0)
    return buf

def _compose_profile(
    party_sprites: List[bytes],
    background: Image.Image,
    coords: List[Tuple[int, int, int, int]] = PROFILE_COORDS,
) -> io.BytesIO:
    composed = background.copy()
    
    for i, sprite_bytes in enumerate(party_sprites):
        if i >= len(coords) or not sprite_bytes:
            break
        x, y, w, h = coords[i]
        spr = _process_sprite_crop(
            sprite_bytes,
            int(w * 0.6),
            int(h * 0.8),
            crop=True,
            scale_boost=1.0,
            max_height_ratio=1.0,
            force_height=False,
            max_width_ratio=1.0,
            pad=1,
        )
        composed.paste(spr, (x + 30, y + 15), spr)
        spr.close()
        
    buf = io.BytesIO()
    composed.save(buf, format="PNG", optimize=False, compress_level=0)
    composed.close()
    buf.seek(0)
    return buf

def _colorize_sprite_fast(sprite: Image.Image, color: Tuple[int, int, int]) -> Image.Image:
    arr = np.array(sprite, dtype=np.uint8)
    mask = arr[:, :, 3] > 10
    result = np.zeros_like(arr)
    result[:, :, 0] = np.where(mask, color[0], 0)
    result[:, :, 1] = np.where(mask, color[1], 0)
    result[:, :, 2] = np.where(mask, color[2], 0)
    result[:, :, 3] = arr[:, :, 3]
    return Image.fromarray(result, 'RGBA')

def _compose_evolution(
    sprite_from_bytes: bytes,
    sprite_to_bytes: bytes,
    canvas_size: Tuple[int, int] = (400, 400),
    scale_factor: float = 3.0,
) -> io.BytesIO:
    sprite_from_raw = Image.open(io.BytesIO(sprite_from_bytes)).convert("RGBA")
    sprite_to_raw = Image.open(io.BytesIO(sprite_to_bytes)).convert("RGBA")
    
    sprite_from = sprite_from_raw.resize(
        (int(sprite_from_raw.width * scale_factor), int(sprite_from_raw.height * scale_factor)),
        Image.Resampling.NEAREST
    )
    sprite_from_raw.close()
    
    sprite_to = sprite_to_raw.resize(
        (int(sprite_to_raw.width * scale_factor), int(sprite_to_raw.height * scale_factor)),
        Image.Resampling.NEAREST
    )
    sprite_to_raw.close()
    
    def create_canvas_with_sprite(sprite: Image.Image) -> Image.Image:
        canvas = Image.new('RGB', canvas_size, (0, 0, 0))
        sprite_rgb = Image.new('RGB', sprite.size, (0, 0, 0))
        sprite_rgb.paste(sprite, (0, 0), sprite)
        x = (canvas_size[0] - sprite.width) // 2
        y = (canvas_size[1] - sprite.height) // 2
        canvas.paste(sprite_rgb, (x, y))
        return canvas
    
    frames = []
    durations = []
    
    canvas_from = create_canvas_with_sprite(sprite_from)
    white_sprite_from = _colorize_sprite_fast(sprite_from, (255, 255, 255))
    white_canvas_from = create_canvas_with_sprite(white_sprite_from)
    
    for _ in range(5):
        frames.append(canvas_from.copy())
        durations.append(100)
        frames.append(white_canvas_from.copy())
        durations.append(100)
    
    white_sprite_to = _colorize_sprite_fast(sprite_to, (255, 255, 255))
    white_canvas_to = create_canvas_with_sprite(white_sprite_to)
    
    for _ in range(22):
        frames.append(white_canvas_from.copy())
        durations.append(50)
        frames.append(white_canvas_to.copy())
        durations.append(50)
    
    canvas_to = create_canvas_with_sprite(sprite_to)
    
    for i in range(12):
        frame = Image.new('RGB', canvas_size, (0, 0, 0))
        frame.paste(canvas_to, (0, 0))
        intensity = int(255 * (1.0 - (i / 11.0)))
        blend = Image.blend(
            frame, 
            Image.new('RGB', canvas_size, (255, 255, 255)), 
            intensity / 255.0
        )
        frames.append(blend)
        durations.append(60)
    
    frames.append(canvas_to.copy())
    durations.append(2500)
    
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2
    )
    buf.seek(0)
    
    sprite_from.close()
    sprite_to.close()
    white_sprite_from.close()
    white_sprite_to.close()
    
    return buf

async def compose_evolution_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_evolution, *args, **kwargs)

async def compose_pokemon_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_pokemon, *args, **kwargs)

async def compose_battle_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_battle, *args, **kwargs)

async def compose_profile_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_profile, *args, **kwargs)
