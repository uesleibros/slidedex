from typing import Callable
from functools import reduce
from sdk.calculations import IVCalculator

class FilterConfig:
	STAT_IV_MAP = {
		"hpiv": "hp",
		"atkiv": "attack",
		"defiv": "defense",
		"spatkiv": "special-attack",
		"spdefiv": "special-defense",
		"spdiv": "speed"
	}
	
	STAT_EV_MAP = {
		"hpev": "hp",
		"atkev": "attack",
		"defev": "defense",
		"spatkev": "special-attack",
		"spdefev": "special-defense",
		"spedev": "speed"
	}

class PokemonFilter:
	@staticmethod
	def _parse_values(flag_value) -> list:
		if isinstance(flag_value, list):
			return [int(v) for group in flag_value for v in (group if isinstance(group, list) else [group])]
		return [flag_value]
	
	@staticmethod
	def _parse_strings(flag_value) -> list[str]:
		if isinstance(flag_value, list):
			return [str(v).lower() for group in flag_value for v in (group if isinstance(group, list) else [group])]
		return [str(flag_value).lower()]
	
	@staticmethod
	def boolean_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		filters = {
			"favorite": lambda p: p.get("is_favorite", False),
			"shiny": lambda p: p.get("is_shiny", False),
			"legendary": lambda p: p.get("is_legendary", False),
			"mythical": lambda p: p.get("is_mythical", False),
			"no_nickname": lambda p: not p.get("nickname"),
			"has_nickname": lambda p: bool(p.get("nickname")),
			"no_held_item": lambda p: not p.get("held_item"),
			"has_held_item": lambda p: bool(p.get("held_item")),
			"fainted": lambda p: p.get("current_hp", 0) <= 0,
		}
		
		result = pokemons
		for flag_name, filter_func in filters.items():
			if flags.get(flag_name):
				result = [p for p in result if filter_func(p)]
		
		return result
	
	@staticmethod
	def range_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		result = pokemons
		
		range_configs = [
			("min_iv", "max_iv", lambda p: IVCalculator.percentage(p["ivs"])),
			("min_level", "max_level", lambda p: p["level"]),
			("min_happiness", "max_happiness", lambda p: p.get("happiness", 0)),
			("min_ev", "max_ev", lambda p: sum(p.get("evs", {}).values())),
			("min_exp", "max_exp", lambda p: p.get("exp", 0)),
			("min_move_count", "max_move_count", lambda p: len(p.get("moves", []))),
		]
		
		for min_key, max_key, getter in range_configs:
			if flags.get(min_key) is not None:
				result = [p for p in result if getter(p) >= flags[min_key]]
			if flags.get(max_key) is not None:
				result = [p for p in result if getter(p) <= flags[max_key]]
		
		return result
	
	@staticmethod
	def exact_value_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		result = pokemons
		
		exact_configs = [
			("level", lambda p: p["level"]),
			("happiness", lambda p: p.get("happiness", 0)),
			("exp", lambda p: p.get("exp", 0)),
			("move_count", lambda p: len(p.get("moves", []))),
			("species", lambda p: p.get("species_id")),
		]
		
		for flag_name, getter in exact_configs:
			if flags.get(flag_name):
				values = PokemonFilter._parse_values(flags[flag_name])
				result = [p for p in result if getter(p) in values]
		
		if flags.get("iv"):
			iv_values = PokemonFilter._parse_values(flags["iv"])
			result = [p for p in result if int(IVCalculator.percentage(p["ivs"])) in iv_values]
		
		return result
	
	@staticmethod
	def stat_iv_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		result = pokemons
		
		for flag_name, stat_key in FilterConfig.STAT_IV_MAP.items():
			if flags.get(flag_name):
				values = PokemonFilter._parse_values(flags[flag_name])
				result = [p for p in result if p["ivs"].get(stat_key, 0) in values]
		
		return result
	
	@staticmethod
	def stat_ev_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		result = pokemons
		
		for flag_name, stat_key in FilterConfig.STAT_EV_MAP.items():
			if flags.get(flag_name):
				values = PokemonFilter._parse_values(flags[flag_name])
				result = [p for p in result if p.get("evs", {}).get(stat_key, 0) in values]
		
		return result
	
	@staticmethod
	def string_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		result = pokemons
		
		if flags.get("gender"):
			gender = flags["gender"].lower()
			result = [p for p in result if p["gender"].lower() == gender]
		
		if flags.get("name"):
			names = PokemonFilter._parse_strings(flags["name"])
			result = [p for p in result if any(q in (p.get("name", "")).lower() for q in names)]
		
		if flags.get("nickname"):
			nicks = PokemonFilter._parse_strings(flags["nickname"])
			result = [p for p in result if any(q in (p.get("nickname", "") or "").lower() for q in nicks)]
		
		if flags.get("type"):
			types = PokemonFilter._parse_strings(flags["type"])
			result = [p for p in result if any(ptype.lower() in types for ptype in p.get("types", []))]
		
		if flags.get("region"):
			regions = PokemonFilter._parse_strings(flags["region"])
			result = [p for p in result if any(q in (p.get("region", "")).lower() for q in regions)]
		
		if flags.get("nature"):
			natures = PokemonFilter._parse_strings(flags["nature"])
			result = [p for p in result if p["nature"].lower() in natures]
		
		if flags.get("ability"):
			abilities = PokemonFilter._parse_strings(flags["ability"])
			result = [p for p in result if p["ability"].lower() in abilities]
		
		if flags.get("held_item"):
			items = PokemonFilter._parse_strings(flags["held_item"])
			result = [p for p in result if p.get("held_item") and p["held_item"].lower() in items]
		
		if flags.get("growth_type"):
			growth_types = PokemonFilter._parse_strings(flags["growth_type"])
			result = [p for p in result if p.get("growth_type", "").lower() in growth_types]
		
		if flags.get("background"):
			backgrounds = PokemonFilter._parse_strings(flags["background"])
			result = [p for p in result if p.get("background", "").lower() in backgrounds]
		
		return result
	
	@staticmethod
	def complex_filters(pokemons: list[dict], flags: dict) -> list[dict]:
		result = pokemons
		
		if flags.get("move"):
			moves = [m.lower().replace(" ", "-") for m in PokemonFilter._parse_strings(flags["move"])]
			result = [
				p for p in result
				if any(move.get("id", "").lower() in moves for move in p.get("moves", []))
			]
		
		if flags.get("exp_percent"):
			percent_values = PokemonFilter._parse_values(flags["exp_percent"])
			filtered = []
			for p in result:
				progress = tk.get_exp_progress(p.get("growth_type", "medium"), p.get("exp", 0))
				if int(progress["progress_percent"]) in percent_values:
					filtered.append(p)
			result = filtered
		
		# IV special filters
		iv_filters = {
			"triple_31": lambda ivs: sum(1 for v in ivs.values() if v == 31) >= 3,
			"quad_31": lambda ivs: sum(1 for v in ivs.values() if v == 31) >= 4,
			"penta_31": lambda ivs: sum(1 for v in ivs.values() if v == 31) >= 5,
			"hexa_31": lambda ivs: sum(1 for v in ivs.values() if v == 31) == 6,
			"triple_0": lambda ivs: sum(1 for v in ivs.values() if v == 0) >= 3,
			"quad_0": lambda ivs: sum(1 for v in ivs.values() if v == 0) >= 4,
		}
		
		for flag_name, filter_func in iv_filters.items():
			if flags.get(flag_name):
				result = [p for p in result if filter_func(p["ivs"])]
		
		# Duplicates/Unique
		if flags.get("duplicates") or flags.get("unique"):
			species_count = {}
			for p in pokemons:
				sid = p["species_id"]
				species_count[sid] = species_count.get(sid, 0) + 1
			
			if flags.get("duplicates"):
				result = [p for p in result if species_count.get(p["species_id"], 0) > 1]
			elif flags.get("unique"):
				result = [p for p in result if species_count.get(p["species_id"], 0) == 1]
		
		return result

def apply_filters(pokemons: list[dict], flags: dict) -> list[dict]:
	filters = [
		PokemonFilter.boolean_filters,
		PokemonFilter.range_filters,
		PokemonFilter.exact_value_filters,
		PokemonFilter.stat_iv_filters,
		PokemonFilter.stat_ev_filters,
		PokemonFilter.string_filters,
		PokemonFilter.complex_filters,
	]
	
	result = pokemons
	for filter_func in filters:
		result = filter_func(result, flags)
	
	return result

def apply_sort_limit(pokemons: list[dict], flags: dict) -> list[dict]:
	result = list(pokemons)
	
	if flags.get("random"):
		import random
		random.shuffle(result)
	elif flags.get("sort"):
		sort_keys = {
			"iv": lambda p: IVCalculator.percentage(p["ivs"]),
			"level": lambda p: p["level"],
			"id": lambda p: p["id"],
			"name": lambda p: (p.get("nickname") or p.get("name", "")).lower(),
			"species": lambda p: p["species_id"],
			"ev": lambda p: sum(p.get("evs", {}).values()),
			"hp": lambda p: p.get("current_hp", 0),
			"exp": lambda p: p.get("exp", 0),
			"growth": lambda p: p.get("growth_type", ""),
			"happiness": lambda p: p.get("happiness", 0),
		}
		
		sort_key = sort_keys.get(flags["sort"], lambda p: p["id"])
		result.sort(key=sort_key, reverse=bool(flags.get("reverse")))
	
	if flags.get("limit") and flags["limit"] > 0:
		result = result[:flags["limit"]]
	
	return result