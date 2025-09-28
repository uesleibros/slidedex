from PIL import Image
from typing import Dict

BACKGROUNDS: Dict[str, str] = {
	"grassland": "resources/backgrounds/route.jpg",
	"forest": "resources/backgrounds/forest.jpg",
	"cave": "resources/backgrounds/cave.jpg",
	"mountain": "resources/backgrounds/cave.jpg",
	"sea": "resources/backgrounds/sea.jpg",
	"urban": "resources/backgrounds/urban.png",
	"rare": "resources/backgrounds/rare.png",
	"rough-terrain": "resources/backgrounds/rough_terrain.png",
	"waters-edge": "resources/backgrounds/beach.png",
}

INFO_BACKGROUNDS: Dict[str, str] = {
	"lab": "resources/backgrounds/info/lab.png",
	"gen2": "resources/backgrounds/info/gen2.jpg",
}

TEXTURES: Dict[str, str] = {
	"battle": "resources/textures/battle.png",
	"profile": "resources/textures/profile.png"
}

preloaded_backgrounds: Dict[str, Image.Image] = {}
preloaded_info_backgrounds: Dict[str, Image.Image] = {}
preloaded_textures: Dict[str, Image.Image] = {}

TARGET_SIZE = (400, 225)
CONVERT_MODE = "RGBA"
RESAMPLE = Image.Resampling.NEAREST


def preload(mapping: Dict[str, str], cache: Dict[str, Image.Image], resize: bool = True) -> None:
	for key, path in mapping.items():
		if key in cache:
			continue
		with Image.open(path) as img:
			if resize:
				cache[key] = img.convert(CONVERT_MODE).resize(TARGET_SIZE, RESAMPLE)
			else:
				cache[key] = img.convert(CONVERT_MODE)

def preload_backgrounds() -> None:
	preload(BACKGROUNDS, preloaded_backgrounds)

def preload_info_backgrounds() -> None:
	preload(INFO_BACKGROUNDS, preloaded_info_backgrounds)

def preload_textures() -> None:
	preload(TEXTURES, preloaded_textures, False)