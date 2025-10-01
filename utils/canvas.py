import io
import asyncio
from typing import List, Tuple
from PIL import Image, ImageOps

PROFILE_COORDS: List[Tuple[int, int, int, int]] = [
	(5, -8, 137, 83),   # slot 1
	(150, -8, 137, 83), # slot 2
	(290, -8, 137, 83), # slot 3
	(5, 71, 137, 83),   # slot 4
	(150, 71, 137, 83), # slot 5
	(290, 71, 137, 83), # slot 6
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

def _compose_pokemon(
	sprite_bytes: bytes,
	background: Image.Image,
	box_size: int = 200,
	ground_y: int = 205
) -> io.BytesIO:
	composed = background.copy()
	try:
		spr = _to_box(sprite_bytes, box_size)
		x = (composed.width - spr.width) // 2
		y = ground_y - spr.height
		composed.paste(spr, (x, y), spr)
		buf = io.BytesIO()
		composed.save(buf, format="PNG", optimize=False, compress_level=1)
		buf.seek(0)
		return buf
	finally:
		composed.close()

def _process_sprite_crop(sprite_bytes: bytes, w: int, h: int, crop: bool = True) -> Image.Image:
	im = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
	try:
		if crop:
			cw, ch = im.size
			crop_h = int(ch / 1.6)
			im = im.crop((0, 0, cw, crop_h))

		sf = min(w / im.width, h / im.height)
		nw, nh = int(im.width * sf), int(im.height * sf)
		res = im.resize((nw, nh), Image.Resampling.NEAREST)

		final = Image.new("RGBA", (w, h), (0, 0, 0, 0))
		x = (w - nw) // 2
		y = h - nh
		final.paste(res, (x, y), res)
		return final
	finally:
		im.close()

def _compose_battle(
	player_bytes: bytes,
	enemy_bytes: bytes,
	background: Image.Image,
	box_size: int = 170,
	player_ground_y: int = 300,
	enemy_ground_y: int = 170,
	player_x: int = 20,
	enemy_x: int = 270
) -> io.BytesIO:
	composed = background.copy()
	try:
		if player_bytes:
			player_box_size = int(box_size * 1.6)
			p = _process_sprite_crop(player_bytes, player_box_size, player_box_size, crop=False)
			composed.paste(p, (player_x, player_ground_y - p.height), p)
		if enemy_bytes:
			enemy_box_size = int(box_size * 1.2)
			e = _process_sprite_crop(enemy_bytes, enemy_box_size, enemy_box_size, crop=False)
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
            spr = _process_sprite_crop(sprite_bytes, w, h)
            composed.paste(spr, (x, y), spr)

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
