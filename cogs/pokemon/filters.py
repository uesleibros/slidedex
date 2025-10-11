import random
from typing import Dict, List
from pokemon_sdk.calculations import iv_percent
from pokemon_sdk.config import tk


def apply_filters(pokemons: List[Dict], flags) -> List[Dict]:
	res = pokemons
	
	if flags.get("favorite"):
		res = [p for p in res if p.get("is_favorite")]
	if flags.get("shiny"):
		res = [p for p in res if p.get("is_shiny", False)]
	if flags.get("legendary"):
		res = [p for p in res if p.get("is_legendary", False)]
	if flags.get("mythical"):
		res = [p for p in res if p.get("is_mythical", False)]
	if flags.get("gender"):
		res = [p for p in res if p["gender"].lower() == flags.get("gender").lower()]
	
	if flags.get("min_iv") is not None:
		res = [p for p in res if iv_percent(p["ivs"]) >= flags.get("min_iv")]
	if flags.get("max_iv") is not None:
		res = [p for p in res if iv_percent(p["ivs"]) <= flags.get("max_iv")]
	
	if flags.get("min_level") is not None:
		res = [p for p in res if p["level"] >= flags.get("min_level")]
	if flags.get("max_level") is not None:
		res = [p for p in res if p["level"] <= flags.get("max_level")]
	if flags.get("level"):
		levels = [int(v) for group in flags["level"] for v in group]
		res = [p for p in res if p["level"] in levels]
	
	if flags.get("min_happiness") is not None:
		res = [p for p in res if p.get("happiness", 0) >= flags.get("min_happiness")]
	if flags.get("max_happiness") is not None:
		res = [p for p in res if p.get("happiness", 0) <= flags.get("max_happiness")]
	if flags.get("happiness"):
		happiness_values = [int(v) for group in flags["happiness"] for v in group]
		res = [p for p in res if p.get("happiness", 0) in happiness_values]
	
	if flags.get("hpiv"):
		hp_values = [int(v) for group in flags["hpiv"] for v in group]
		res = [p for p in res if p["ivs"]["hp"] in hp_values]
	if flags.get("atkiv"):
		atk_values = [int(v) for group in flags["atkiv"] for v in group]
		res = [p for p in res if p["ivs"]["attack"] in atk_values]
	if flags.get("defiv"):
		def_values = [int(v) for group in flags["defiv"] for v in group]
		res = [p for p in res if p["ivs"]["defense"] in def_values]
	if flags.get("spatkiv"):
		spatk_values = [int(v) for group in flags["spatkiv"] for v in group]
		res = [p for p in res if p["ivs"]["special-attack"] in spatk_values]
	if flags.get("spdefiv"):
		spdef_values = [int(v) for group in flags["spdefiv"] for v in group]
		res = [p for p in res if p["ivs"]["special-defense"] in spdef_values]
	if flags.get("spdiv"):
		spd_values = [int(v) for group in flags["spdiv"] for v in group]
		res = [p for p in res if p["ivs"]["speed"] in spd_values]
	if flags.get("iv"):
		iv_values = [int(v) for group in flags["iv"] for v in group]
		res = [p for p in res if int(iv_percent(p["ivs"])) in iv_values]
	
	if flags.get("min_ev") is not None:
		res = [p for p in res if sum(p.get("evs", {}).values()) >= flags.get("min_ev")]
	if flags.get("max_ev") is not None:
		res = [p for p in res if sum(p.get("evs", {}).values()) <= flags.get("max_ev")]
	
	if flags.get("hpev"):
		hp_values = [int(v) for group in flags["hpev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("hp", 0) in hp_values]
	if flags.get("atkev"):
		atk_values = [int(v) for group in flags["atkev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("attack", 0) in atk_values]
	if flags.get("defev"):
		def_values = [int(v) for group in flags["defev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("defense", 0) in def_values]
	if flags.get("spatkev"):
		spatk_values = [int(v) for group in flags["spatkev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("special-attack", 0) in spatk_values]
	if flags.get("spdefev"):
		spdef_values = [int(v) for group in flags["spdefev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("special-defense", 0) in spdef_values]
	if flags.get("spedev"):
		spd_values = [int(v) for group in flags["spedev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("speed", 0) in spd_values]
	
	if flags.get("species") is not None:
		species = [int(s) for group in flags["species"] for s in group]
		res = [p for p in res if p.get("species_id") in species]
	
	if flags.get("name"):
		names = [n.lower() for group in flags["name"] for n in group]
		res = [
			p for p in res
			if any(q in (p.get("name", "")).lower() for q in names)
		]
	
	if flags.get("type"):
		types = [t.lower() for group in flags["type"] for t in group]
		res = [p for p in res if any(ptype.lower() in types for ptype in p["types"])]
	
	if flags.get("region"):
		regions = [r.lower() for group in flags["region"] for r in group]
		res = [
			p for p in res
			if any(q in (p.get("region", "")).lower() for q in regions)
		]
	
	if flags.get("nickname"):
		nicks = [n.lower() for group in flags["nickname"] for n in group]
		res = [
			p for p in res
			if any(q in (p.get("nickname", "") or "").lower() for q in nicks)
		]
	
	if flags.get("nature"):
		natures = [n.lower() for group in flags["nature"] for n in group]
		res = [p for p in res if any(p["nature"].lower() == nat for nat in natures)]
	
	if flags.get("ability"):
		abilities = [a.lower() for group in flags["ability"] for a in (group if isinstance(group, list) else [group])]
		res = [p for p in res if any(p["ability"].lower() == ab for ab in abilities)]
	
	if flags.get("held_item"):
		held_items = [h.lower() for group in flags["held_item"] for h in (group if isinstance(group, list) else [group])]
		res = [p for p in res if p.get("held_item") and any(p["held_item"].lower() == hi for hi in held_items)]
	
	if flags.get("move"):
		moves = [m.lower().replace(" ", "-") for group in flags["move"] for m in group]
		res = [
			p for p in res
			if any(
				move_id.lower() in moves 
				for move in p.get("moves", []) 
				for move_id in [move.get("id", "")]
			)
		]
	
	if flags.get("no_nickname"):
		res = [p for p in res if not p.get("nickname")]
	if flags.get("has_nickname"):
		res = [p for p in res if p.get("nickname")]
	
	if flags.get("no_held_item"):
		res = [p for p in res if not p.get("held_item")]
	if flags.get("has_held_item"):
		res = [p for p in res if p.get("held_item")]
	
	if flags.get("fainted"):
		res = [p for p in res if p.get("current_hp", 0) <= 0]
	if flags.get("healthy"):
		max_hp = lambda p: p.get("base_stats", {}).get("hp", 0)
		res = [p for p in res if p.get("current_hp", 0) >= max_hp(p)]
	
	if flags.get("growth_type"):
		growth_types = [g.lower() for group in flags["growth_type"] for g in group]
		res = [p for p in res if p.get("growth_type", "").lower() in growth_types]
	
	if flags.get("min_exp") is not None:
		res = [p for p in res if p.get("exp", 0) >= flags.get("min_exp")]
	if flags.get("max_exp") is not None:
		res = [p for p in res if p.get("exp", 0) <= flags.get("max_exp")]
	if flags.get("exp"):
		exp_values = [int(v) for group in flags["exp"] for v in group]
		res = [p for p in res if p.get("exp", 0) in exp_values]
	
	if flags.get("exp_percent") is not None:
		percent_values = [int(v) for group in flags["exp_percent"] for v in group]
		filtered = []
		for p in res:
			progress = tk.get_exp_progress(p.get("growth_type", "medium"), p.get("exp", 0))
			if int(progress["progress_percent"]) in percent_values:
				filtered.append(p)
		res = filtered
	
	if flags.get("background"):
		backgrounds = [b.lower() for group in flags["background"] for b in group]
		res = [p for p in res if p.get("background", "").lower() in backgrounds]
	
	if flags.get("min_move_count") is not None:
		res = [p for p in res if len(p.get("moves", [])) >= flags.get("min_move_count")]
	if flags.get("max_move_count") is not None:
		res = [p for p in res if len(p.get("moves", [])) <= flags.get("max_move_count")]
	if flags.get("move_count"):
		counts = [int(v) for group in flags["move_count"] for v in group]
		res = [p for p in res if len(p.get("moves", [])) in counts]
	
	if flags.get("triple_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) >= 3]
	if flags.get("quad_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) >= 4]
	if flags.get("penta_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) >= 5]
	if flags.get("hexa_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) == 6]
	
	if flags.get("triple_0"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 0) >= 3]
	if flags.get("quad_0"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 0) >= 4]
	
	if flags.get("duplicates"):
		species_count = {}
		for p in pokemons:
			sid = p["species_id"]
			species_count[sid] = species_count.get(sid, 0) + 1
		res = [p for p in res if species_count.get(p["species_id"], 0) > 1]
	
	if flags.get("unique"):
		species_count = {}
		for p in pokemons:
			sid = p["species_id"]
			species_count[sid] = species_count.get(sid, 0) + 1
		res = [p for p in res if species_count.get(p["species_id"], 0) == 1]
	
	return res


def apply_sort_limit(pokemons: List[Dict], flags) -> List[Dict]:
	res = list(pokemons)
	if flags.get("random"):
		random.shuffle(res)
	elif flags.get("sort"):
		keymap = {
			"iv": lambda p: iv_percent(p["ivs"]),
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
		res.sort(key=keymap.get(flags.get("sort"), lambda p: p["id"]), reverse=bool(flags.get("reverse")))
	if flags.get("limit") is not None and flags.get("limit") > 0:
		res = res[:flags.get("limit")]
	return res