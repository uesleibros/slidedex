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

preloaded_backgrounds: Dict[str, Image] = {}

def preload_backgrounds() -> None:
	for key, path in BACKGROUNDS.items():
		preloaded_backgrounds[key] = Image.open(path).convert("RGBA").resize((400, 225), Image.Resampling.NEAREST)