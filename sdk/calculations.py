from typing import Final, Optional
from sdk.constants import NATURES, STAT_KEYS

IV_MAX: Final[int] = 31
IV_TOTAL_PERFECT: Final[int] = 186
HP_STAT: Final[str] = "hp"

STAT_CALCULATION_BASE: Final[int] = 2
STAT_CALCULATION_DIVISOR: Final[int] = 100
EV_DIVISOR: Final[int] = 4

HP_BASE_BONUS: Final[int] = 10
STAT_BASE_BONUS: Final[int] = 5

NATURE_BOOST: Final[float] = 1.1
NATURE_PENALTY: Final[float] = 0.9

class StatCalculator:
	@staticmethod
	def calculate_hp(base: int, iv: int, ev: int, level: int) -> int:
		stat_value = (STAT_CALCULATION_BASE * base + iv + (ev // EV_DIVISOR)) * level
		return int(stat_value / STAT_CALCULATION_DIVISOR) + level + HP_BASE_BONUS
	
	@staticmethod
	def calculate_stat(
		base: int,
		iv: int,
		ev: int,
		level: int,
		nature_modifier: Optional[float] = None
	) -> int:
		stat_value = (STAT_CALCULATION_BASE * base + iv + (ev // EV_DIVISOR)) * level
		result = int(stat_value / STAT_CALCULATION_DIVISOR) + STAT_BASE_BONUS
		
		if nature_modifier:
			result = int(result * nature_modifier)
		
		return result
	
	@staticmethod
	def calculate_all(
		base_stats: dict[str, int],
		ivs: dict[str, int],
		evs: dict[str, int],
		level: int,
		nature: str
	) -> dict[str, int]:
		increased, decreased = NATURES.get(nature, (None, None))
		stats = {}
		
		for stat_name in STAT_KEYS:
			base = base_stats.get(stat_name, 0)
			iv = ivs.get(stat_name, 0)
			ev = evs.get(stat_name, 0)
			
			if stat_name == HP_STAT:
				stats[stat_name] = StatCalculator.calculate_hp(base, iv, ev, level)
			else:
				nature_mod = None
				if increased == stat_name:
					nature_mod = NATURE_BOOST
				elif decreased == stat_name:
					nature_mod = NATURE_PENALTY
				
				stats[stat_name] = StatCalculator.calculate_stat(
					base, iv, ev, level, nature_mod
				)
		
		return stats

class IVCalculator:
	@staticmethod
	def total(ivs: dict[str, int]) -> int:
		return sum(ivs.values())
	
	@staticmethod
	def percentage(ivs: dict[str, int], decimals: int = 2) -> float:
		total = IVCalculator.total(ivs)
		return round((total / IV_TOTAL_PERFECT) * 100.0, decimals)
	
	@staticmethod
	def is_perfect(ivs: dict[str, int]) -> bool:
		return all(iv == IV_MAX for iv in ivs.values())
	
	@staticmethod
	def count_perfect(ivs: dict[str, int]) -> int:
		return sum(1 for iv in ivs.values() if iv == IV_MAX)
	
	@staticmethod
	def get_stats(ivs: dict[str, int]) -> dict:
		return {
			"total": IVCalculator.total(ivs),
			"percentage": IVCalculator.percentage(ivs),
			"is_perfect": IVCalculator.is_perfect(ivs),
			"perfect_count": IVCalculator.count_perfect(ivs)
		}

class HPCalculator:
	@staticmethod
	def adjust_on_level_up(old_max_hp: int, new_max_hp: int, current_hp: int) -> int:
		if current_hp <= 0:
			return 0
		
		if current_hp >= old_max_hp:
			return new_max_hp
		
		hp_ratio = current_hp / old_max_hp
		adjusted_hp = int(new_max_hp * hp_ratio)
		
		return max(1, min(adjusted_hp, new_max_hp))
	
	@staticmethod
	def get_percentage(current_hp: int, max_hp: int) -> float:
		if max_hp <= 0:
			return 0.0
		return round((current_hp / max_hp) * 100.0, 2)
	
	@staticmethod
	def is_fainted(current_hp: int) -> bool:
		return current_hp <= 0
	
	@staticmethod
	def restore(current_hp: int, max_hp: int, amount: int) -> int:
		return min(current_hp + amount, max_hp)
	
	@staticmethod
	def damage(current_hp: int, amount: int) -> int:
		return max(0, current_hp - amount)
	
	@staticmethod
	def get_stats(current_hp: int, max_hp: int) -> dict:
		return {
			"current": current_hp,
			"max": max_hp,
			"percentage": HPCalculator.get_percentage(current_hp, max_hp),
			"is_fainted": HPCalculator.is_fainted(current_hp)
		}

class PokemonDataGenerator:
	@staticmethod
	def generate(
		base_stats: dict[str, int],
		level: int,
		nature: str,
		ivs: dict[str, int],
		evs: Optional[dict[str, int]] = None
	) -> dict:
		if evs is None:
			evs = {stat: 0 for stat in STAT_KEYS}
		
		calculated_stats = StatCalculator.calculate_all(
			base_stats, ivs, evs, level, nature
		)
		
		return {
			"level": level,
			"stats": base_stats,
			"ivs": ivs,
			"evs": evs,
			"nature": nature,
			"current_hp": calculated_stats[HP_STAT]
		}
	
	@staticmethod
	def generate_summary(pokemon: dict) -> dict:
		base_stats = pokemon["base_stats"]
		ivs = pokemon["ivs"]
		evs = pokemon["evs"]
		level = pokemon["level"]
		nature = pokemon["nature"]
		
		calculated_stats = StatCalculator.calculate_all(
			base_stats, ivs, evs, level, nature
		)
		
		current_hp = pokemon.get("current_hp", calculated_stats[HP_STAT])
		max_hp = calculated_stats[HP_STAT]
		
		return {
			"iv_total": IVCalculator.total(ivs),
			"iv_percent": IVCalculator.percentage(ivs),
			"iv_perfect_count": IVCalculator.count_perfect(ivs),
			"is_perfect_ivs": IVCalculator.is_perfect(ivs),
			"ev_total": sum(evs.values()),
			"max_hp": max_hp,
			"current_hp": current_hp,
			"hp_percent": HPCalculator.get_percentage(current_hp, max_hp),
			"is_fainted": HPCalculator.is_fainted(current_hp),
			"calculated_stats": calculated_stats
		}

def calculate_stats(
	base_stats: dict[str, int],
	ivs: dict[str, int],
	evs: dict[str, int],
	level: int,
	nature: str
) -> dict[str, int]:
	return StatCalculator.calculate_all(base_stats, ivs, evs, level, nature)

def generate_pokemon_data(
	base_stats: dict[str, int],
	level: int,
	nature: str,
	ivs: dict[str, int],
	evs: Optional[dict[str, int]] = None
) -> dict:
	return PokemonDataGenerator.generate(base_stats, level, nature, ivs, evs)

def iv_total(ivs: dict[str, int]) -> int:
	return IVCalculator.total(ivs)

def iv_percent(ivs: dict[str, int], decimals: int = 2) -> float:
	return IVCalculator.percentage(ivs, decimals)

def calculate_max_hp(base_hp: int, iv_hp: int, ev_hp: int, level: int) -> int:
	return StatCalculator.calculate_hp(base_hp, iv_hp, ev_hp, level)

def adjust_hp_on_level_up(old_max_hp: int, new_max_hp: int, current_hp: int) -> int:
	return HPCalculator.adjust_on_level_up(old_max_hp, new_max_hp, current_hp)