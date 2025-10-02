import math
import random
from typing import Dict, Optional
from .constants import NATURES

def calculate_stats(base_stats: Dict[str, int], ivs: Dict[str, int], evs: Dict[str, int], level: int, nature: str) -> Dict[str, int]:
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

def generate_pokemon_data(base_stats: Dict[str, int], level: int, nature: str, ivs: Dict[str, int], evs: Optional[Dict[str, int]] = None) -> Dict:
	if evs is None:
		evs = {k: 0 for k in base_stats.keys()}
	stats = calculate_stats(base_stats, ivs, evs, level, nature)
	return {"stats": base_stats, "current_hp": stats["hp"], "ivs": ivs, "evs": evs, "nature": nature, "level": level}

def generate_stats(base_stats: Dict[str, int], level: int) -> Dict:
	ivs = {stat: random.randint(0, 31) for stat in base_stats}
	evs = {stat: 0 for stat in base_stats}
	nature = random.choice(list(NATURES.keys()))
	stats = calculate_stats(base_stats, ivs, evs, level, nature)
	return {"level": level, "ivs": ivs, "evs": evs, "nature": nature, "stats": base_stats, "current_hp": stats["hp"]}

def iv_total(ivs: Dict[str, int]) -> int:
	return sum(ivs.values())

def iv_percent(ivs: Dict[str, int], decimals: int = 2) -> float:
	return round((iv_total(ivs) / 186) * 100.0, decimals)

def calculate_max_hp(base_hp: int, iv_hp: int, ev_hp: int, level: int) -> int:
	return math.floor(((2 * base_hp + iv_hp + (ev_hp // 4)) * level) / 100) + level + 10

def adjust_hp_on_level_up(old_max_hp: int, new_max_hp: int, current_hp: int) -> int:
	if current_hp <= 0:
		return 0
	
	if current_hp >= old_max_hp:
		return new_max_hp
	
	hp_ratio = current_hp / old_max_hp
	adjusted_hp = math.floor(new_max_hp * hp_ratio)
	
	return max(1, min(adjusted_hp, new_max_hp))