import math
import random
from typing import Dict
from .constants import NATURES

def calculate_stats(base_stats: Dict[str, int], ivs: Dict[str, int], evs: Dict[str, int], level: int, nature: str):
	inc, dec = NATURES.get(nature, (None, None))
	stats = {}
	for stat_name, base in base_stats.items():
		iv = ivs.get(stat_name, 0)
		ev = evs.get(stat_name, 0)
		if stat_name == "hp":
			value = math.floor(((2 * base + iv + (ev // 4)) * level) / 100) + level + 10
		else:
			value = math.floor(((2 * base + iv + (ev // 4)) * level) / 100) + 5
			if inc == stat_name:
				value = math.floor(value * 1.1)
			if dec == stat_name:
				value = math.floor(value * 0.9)
		stats[stat_name] = value
	return stats

def generate_pokemon_data(base_stats: Dict[str, int], level: int, nature: str, ivs: Dict[str, int], evs: Dict[str, int] = None):
	if evs is None:
		evs = {k: 0 for k in base_stats.keys()}
	stats = calculate_stats(base_stats, ivs, evs, level, nature)
	return {"stats": stats, "current_hp": stats["hp"], "ivs": ivs, "evs": evs, "nature": nature, "level": level}

def generate_stats(base_stats: Dict[str, int], level: int):
	ivs = {stat: random.randint(0, 31) for stat in base_stats}
	evs = {stat: 0 for stat in base_stats}
	nature = random.choice(list(NATURES.keys()))
	stats = calculate_stats(base_stats, ivs, evs, level, nature)
	return {"level": level, "ivs": ivs, "evs": evs, "nature": nature, "stats": stats, "current_hp": stats["hp"]}

def iv_total(ivs: Dict[str, int]) -> int:
	return sum(ivs.values())

def iv_percent(ivs: Dict[str, int], decimals: int = 2) -> float:
	return round((iv_total(ivs) / 186) * 100.0, decimals)