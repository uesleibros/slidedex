import io
import asyncio
from typing import List, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps

PROFILE_COORDS: List[Tuple[int, int, int, int]] = [
	(5, -8, 137, 83),
	(150, -8, 137, 83),
	(290, -8, 137, 83),
	(5, 71, 137, 83),
	(150, 71, 137, 83),
	(290, 71, 137, 83)
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

def _draw_hud(draw: ImageDraw.Draw, font: ImageFont, font_small: ImageFont, x: int, y: int, pokemon_data: Dict):
    name = pokemon_data.get("nickname") or pokemon_data.get("name", "Pokémon").title()
    level = pokemon_data.get("level", 5)
    current_hp = pokemon_data.get("current_hp", 50)
    max_hp = pokemon_data.get("stats", {}).get("hp", 50)

    box_width, box_height = 200, 60
    draw.rectangle([x, y, x + box_width, y + box_height], fill=(248, 248, 248), outline=(56, 56, 56), width=2)
    draw.rectangle([x + 2, y + 2, x + box_width - 2, y + box_height - 2], fill=(248, 248, 248), outline=(168, 168, 168), width=2)

    draw.text((x + 15, y + 5), f"{name}", fill=(56, 56, 56), font=font)
    draw.text((x + 130, y + 8), f"Lv{level}", fill=(56, 56, 56), font=font_small)

    bar_x, bar_y = x + 15, y + 35
    bar_width, bar_height = 170, 12
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(56, 56, 56))
    
    ratio = current_hp / max_hp if max_hp > 0 else 0
    hp_color = (88, 208, 128)
    if ratio < 0.5:
        hp_color = (248, 224, 56)
    if ratio < 0.2:
        hp_color = (240, 88, 56)
    
    filled_width = int(bar_width * ratio)
    if filled_width > 4:
        draw.rectangle([bar_x + 2, bar_y + 2, bar_x + filled_width - 2, bar_y + bar_height - 2], fill=hp_color)

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

def _compose_battle(
	player_bytes: bytes,
	enemy_bytes: bytes,
	background: Image.Image,
	player_data: Dict,
	enemy_data: Dict,
	box_size: int = 170,
	player_ground_y: int = 300,
	enemy_ground_y: int = 170,
	player_x: int = 20,
	enemy_x: int = 270
) -> io.BytesIO:
	composed = background.copy()
	draw = ImageDraw.Draw(composed)
	try:
		font = ImageFont.truetype("resources/fonts/DejaVuSans.ttf", 16)
		font_small = ImageFont.truetype("resources/fonts/DejaVuSans.ttf", 14)
	except IOError:
		font = ImageFont.load_default()
		font_small = ImageFont.load_default()

	_draw_hud(draw, font, font_small, x=220, y=150, pokemon_data=player_data)
	_draw_hud(draw, font, font_small, x=10, y=10, pokemon_data=enemy_data)
	
	if player_bytes:
		p = _to_box(player_bytes, int(box_size * 1.5))
		composed.paste(p, (player_x, player_ground_y - p.height), p)
	if enemy_bytes:
		e = _to_box(enemy_bytes, box_size)
		composed.paste(e, (enemy_x, enemy_ground_y - e.height), e)
		
	buf = io.BytesIO()
	composed.save(buf, format="PNG", optimize=False, compress_level=1)
	buf.seek(0)
	return buf

def _process_sprite_crop(sprite_bytes: bytes, w: int, h: int) -> Image.Image:
    im = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
    try:
        cw, ch = im.size
        crop_h = int(ch / 1.6)
        crop = im.crop((0, 0, cw, crop_h))
        sf = min(w / crop.width, h / crop.height) if crop.width > 0 and crop.height > 0 else 0
        nw, nh = int(crop.width * sf), int(crop.height * sf)
        res = crop.resize((nw, nh), Image.Resampling.NEAREST)
        final = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        final.paste(res, ((w - nw) // 2, (h - nh) // 2), res)
        return final
    finally:
        im.close()

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