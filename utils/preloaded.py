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
	"profile": "resources/textures/profile.png"
}

BATTLE_TEXTURES_ARENA: Dict[str, str] = {
	"grassland": "resources/textures/battle/route.png",
	"forest": "resources/textures/battle/route.png",
	"waters-edge": "resources/textures/battle/waters-edge.png",
	"cave": "resources/textures/battle/cave.png",
	"mountain": "resources/textures/battle/cave.png",
	"rough-terrain": "resources/textures/battle/rough_terrain.png",
	"rare": "resources/textures/battle/rare.png",
	"sea": "resources/textures/battle/sea.png",
	"gym": "resources/textures/battle/gym.png",
	"urban": "resources/textures/battle/urban.png",
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