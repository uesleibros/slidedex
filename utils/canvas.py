import io
import asyncio
from typing import List, Tuple
from PIL import Image, ImageOps

PROFILE_COORDS: List[Tuple[int, int, int, int]] = [
    (5, -8, 137, 83),
    (150, -8, 137, 83),
    (290, -8, 137, 83),
    (5, 71, 137, 83),
    (150, 71, 137, 83),
    (290, 71, 137, 83),
]

def _to_box(sprite_bytes: bytes, box: int) -> Image.Image:
    im = Image.open(io.BytesIO(sprite_bytes))
    try:
        im = im.convert("RGBA")
        im = ImageOps.contain(im, (box, box), method=Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (box, box), (0, 0, 0, 0))
        x = (box - im.width) // 2
        y = box - im.height
        canvas.paste(im, (x, y), im)
        return canvas
    finally:
        im.close()

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
    try:
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
        final = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        x = (w - nw) // 2
        y = h - nh
        final.paste(res, (x, y), res)
        return final
    finally:
        im.close()

def _compose_pokemon(
    sprite_bytes: bytes,
    background: Image.Image,
    box_size: int = 180,
    ground_y: int = 180,
    scale_boost: float = 1.0
) -> io.BytesIO:
    composed = background.copy()
    try:
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
        x = (composed.width - spr.width) // 2
        y = ground_y - spr.height
        composed.paste(spr, (x, y), spr)
        buf = io.BytesIO()
        composed.save(buf, format="PNG", optimize=False, compress_level=1)
        buf.seek(0)
        return buf
    finally:
        composed.close()

def _compose_battle(
    player_bytes: bytes,
    enemy_bytes: bytes,
    background: Image.Image,
    box_size: int = 170,
    player_ground_y: int = 250,
    enemy_ground_y: int = 130,
    player_x: int = 20,
    enemy_x: int = 260
) -> io.BytesIO:
    composed = background.copy()
    try:
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
        buf = io.BytesIO()
        composed.save(buf, format="PNG", optimize=False, compress_level=1)
        buf.seek(0)
        return buf
    finally:
        composed.close()

def _compose_profile(
    party_sprites: List[bytes],
    background: Image.Image,
    coords: List[Tuple[int, int, int, int]] = PROFILE_COORDS,
) -> io.BytesIO:
    composed = background.copy()
    try:
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
            composed.paste(spr, (x + 35, y + 15), spr)
        buf = io.BytesIO()
        composed.save(buf, format="PNG", optimize=False, compress_level=1)
        buf.seek(0)
        return buf
    finally:
        composed.close()

async def compose_pokemon_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_pokemon, *args, **kwargs)

async def compose_battle_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_battle, *args, **kwargs)

async def compose_profile_async(*args, **kwargs) -> io.BytesIO:
    return await asyncio.to_thread(_compose_profile, *args, **kwargs)

