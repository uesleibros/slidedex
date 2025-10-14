import io
import asyncio
import numpy as np
from typing import List, Tuple, Optional
from PIL import Image, ImageOps
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import hashlib

PROFILE_COORDS: List[Tuple[int, int, int, int]] = [
	(5, -8, 137, 83),
	(150, -8, 137, 83),
	(290, -8, 137, 83),
	(5, 71, 137, 83),
	(150, 71, 137, 83),
	(290, 71, 137, 83),
]

_executor: Optional[ThreadPoolExecutor] = None

def get_executor() -> ThreadPoolExecutor:
	global _executor
	if _executor is None:
		_executor = ThreadPoolExecutor(max_workers=6)
	return _executor

@lru_cache(maxsize=512)
def _get_sprite_hash(sprite_bytes: bytes) -> str:
	return hashlib.md5(sprite_bytes).hexdigest()[:16]

@lru_cache(maxsize=1024)
def _load_and_convert(sprite_bytes: bytes) -> Image.Image:
	return Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")

def _to_box_optimized(sprite_bytes: bytes, box: int) -> Image.Image:
	im = _load_and_convert(sprite_bytes)
	im = ImageOps.contain(im, (box, box), method=Image.Resampling.NEAREST)
	
	canvas = Image.new("RGBA", (box, box), (0, 0, 0, 0))
	x = (box - im.width) // 2
	y = box - im.height
	canvas.paste(im, (x, y), im)
	return canvas

def _process_sprite_crop_optimized(
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
	im = _load_and_convert(sprite_bytes)
	
	bbox = im.getbbox()
	if bbox:
		l, t, r, b = bbox
		im = im.crop((
			max(0, l - pad),
			max(0, t - pad),
			min(im.width, r + pad),
			min(im.height, b + pad)
		))
	
	if crop:
		cw, ch = im.size
		im = im.crop((0, 0, cw, int(ch / 1.6)))
	
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
	final.paste(res, ((w - nw) // 2, h - nh), res)
	
	return final

def _compose_pokemon_optimized(
	sprite_bytes: bytes,
	background: Image.Image,
	box_size: int = 130,
	ground_y: int = 180,
	scale_boost: float = 1.0
) -> io.BytesIO:
	spr = _process_sprite_crop_optimized(
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
	composed.paste(spr, ((composed.width - spr.width) // 2, ground_y - spr.height), spr)
	
	buf = io.BytesIO()
	composed.save(buf, format="PNG", optimize=False, compress_level=1)
	buf.seek(0)
	return buf

def _compose_battle_optimized(
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
		p = _process_sprite_crop_optimized(
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
		e = _process_sprite_crop_optimized(
			enemy_bytes,
			box_size,
			box_size,
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

def _compose_profile_optimized(
	party_sprites: List[bytes],
	background: Image.Image,
	coords: List[Tuple[int, int, int, int]] = PROFILE_COORDS,
) -> io.BytesIO:
	composed = background.copy()
	
	for i, sprite_bytes in enumerate(party_sprites):
		if i >= len(coords) or not sprite_bytes:
			break
		
		x, y, w, h = coords[i]
		spr = _process_sprite_crop_optimized(
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
	
	buf = io.BytesIO()
	composed.save(buf, format="PNG", optimize=False, compress_level=1)
	buf.seek(0)
	return buf

def _colorize_sprite_numpy(sprite: Image.Image, color: Tuple[int, int, int]) -> Image.Image:
	arr = np.array(sprite, dtype=np.uint8)
	mask = arr[:, :, 3] > 10
	result = np.zeros_like(arr)
	result[:, :, :3][mask] = color
	result[:, :, 3] = arr[:, :, 3]
	return Image.fromarray(result, 'RGBA')

def _compose_evolution_optimized(
	sprite_from_bytes: bytes,
	sprite_to_bytes: bytes,
	canvas_size: Tuple[int, int] = (400, 400),
	scale_factor: float = 3.0,
) -> io.BytesIO:
	sprite_from_raw = _load_and_convert(sprite_from_bytes)
	sprite_to_raw = _load_and_convert(sprite_to_bytes)
	
	from_w, from_h = int(sprite_from_raw.width * scale_factor), int(sprite_from_raw.height * scale_factor)
	to_w, to_h = int(sprite_to_raw.width * scale_factor), int(sprite_to_raw.height * scale_factor)
	
	sprite_from = sprite_from_raw.resize((from_w, from_h), Image.Resampling.NEAREST)
	sprite_to = sprite_to_raw.resize((to_w, to_h), Image.Resampling.NEAREST)
	
	white_sprite_from = _colorize_sprite_numpy(sprite_from, (255, 255, 255))
	white_sprite_to = _colorize_sprite_numpy(sprite_to, (255, 255, 255))
	
	def create_canvas_fast(sprite: Image.Image) -> Image.Image:
		canvas = Image.new('RGB', canvas_size, (0, 0, 0))
		sprite_rgb = Image.new('RGB', sprite.size, (0, 0, 0))
		sprite_rgb.paste(sprite, (0, 0), sprite)
		x = (canvas_size[0] - sprite.width) // 2
		y = (canvas_size[1] - sprite.height) // 2
		canvas.paste(sprite_rgb, (x, y))
		return canvas
	
	canvas_from = create_canvas_fast(sprite_from)
	canvas_to = create_canvas_fast(sprite_to)
	white_canvas_from = create_canvas_fast(white_sprite_from)
	white_canvas_to = create_canvas_fast(white_sprite_to)
	
	frames = []
	durations = []
	
	for _ in range(3):
		frames.extend([canvas_from, white_canvas_from])
		durations.extend([100, 100])
	
	for _ in range(15):
		frames.extend([white_canvas_from, white_canvas_to])
		durations.extend([50, 50])
	
	white_canvas_np = np.array(Image.new('RGB', canvas_size, (255, 255, 255)), dtype=np.uint8)
	canvas_to_np = np.array(canvas_to, dtype=np.uint8)
	
	for i in range(8):
		alpha = 1.0 - (i / 7.0)
		blended = (canvas_to_np * (1 - alpha) + white_canvas_np * alpha).astype(np.uint8)
		frames.append(Image.fromarray(blended, 'RGB'))
		durations.append(60)
	
	frames.append(canvas_to)
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
	return buf

async def compose_evolution_async(*args, **kwargs) -> io.BytesIO:
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(get_executor(), _compose_evolution_optimized, *args, **kwargs)

async def compose_pokemon_async(*args, **kwargs) -> io.BytesIO:
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(get_executor(), _compose_pokemon_optimized, *args, **kwargs)

async def compose_battle_async(*args, **kwargs) -> io.BytesIO:
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(get_executor(), _compose_battle_optimized, *args, **kwargs)

async def compose_profile_async(*args, **kwargs) -> io.BytesIO:
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(get_executor(), _compose_profile_optimized, *args, **kwargs)

async def compose_pokemon_batch(
	sprites_and_backgrounds: List[Tuple[bytes, Image.Image]],
	**kwargs
) -> List[io.BytesIO]:
	tasks = [
		compose_pokemon_async(sprite, bg, **kwargs)
		for sprite, bg in sprites_and_backgrounds
	]
	return await asyncio.gather(*tasks)

def cleanup_executor():
	global _executor
	if _executor:
		_executor.shutdown(wait=True)
		_executor = None