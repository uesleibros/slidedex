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
	"waters-edge": "resources/backgrounds/beach.png"
}

INFO_BACKGROUNDS: Dict[str, str] = {
	"lab": "resources/backgrounds/info/lab.png",
	"gen2": "resources/backgrounds/info/gen2.jpg",
}

preloaded_backgrounds: Dict[str, Image] = {}
preloaded_info_backgrounds: Dict[str, Image] = {}

def preload_backgrounds() -> None:
	for key, path in BACKGROUNDS.items():
		preloaded_backgrounds[key] = Image.open(path).convert("RGBA").resize((400, 225), Image.Resampling.NEAREST)

def preload_info_backgrounds() -> None:
	for key, path in INFO_BACKGROUNDS.items():
		preloaded_info_backgrounds[key] = Image.open(path).convert("RGBA").resize((400, 225), Image.Resampling.NEAREST)