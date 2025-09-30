from typing import Optional, Dict, List, Tuple
from pokemon_sdk.constants import STAT_ALIASES, TYPE_CHART

def _get_stat(stats: Dict[str,int], key: str) -> int:
	for alias in STAT_ALIASES.get(key, []):
		if alias in stats: return int(stats[alias])
	return 1

def _stage_mult(stage: int) -> float:
	return (2+stage)/2 if stage>=0 else 2/(2-stage)

def _apply_stage(base: int, stage: int) -> int:
	return max(1, int(base * _stage_mult(stage)))

def _types_of(p: "BattlePokemon") -> List[str]:
	try: return [t.type.name.lower() for t in p.pokeapi_data.types]
	except: return []

def _type_mult(atk_type: str, def_types: List[str]) -> float:
	atk = (atk_type or "").lower()
	if atk not in TYPE_CHART: return 1.0
	m = 1.0
	for d in def_types:
		if d in TYPE_CHART[atk]["immune"]: return 0.0
		if d in TYPE_CHART[atk]["super"]: m *= 2.0
		elif d in TYPE_CHART[atk]["not"]: m *= 0.5
	return m

def _hp_bar(c: int, t: int, l: int=10) -> str:
	p = 0 if t<=0 else max(0.0, min(1.0, c/t))
	f = int(round(l*p))
	bar = "█"*f + "░"*(l-f)
	return f"`[{bar}]`"

def _slug(move_id: Any) -> str:
	if move_id is None: return ""
	s = str(move_id).strip().lower()
	return s.replace(" ", "-")

class MoveData:
	def __init__(self,
		name: str, accuracy: Optional[int], power: int, priority: int, dmg_class: str, type_name: str,
		min_hits: int, max_hits: int, flinch: int, drain: int, recoil: int, healing: int,
		ailment: Optional[str], ailment_chance: int, stat_changes: List[Tuple[str,int,bool]]
	):
		self.name=name; self.accuracy=accuracy; self.power=power; self.priority=priority
		self.dmg_class=dmg_class; self.type_name=type_name
		self.min_hits=min_hits; self.max_hits=max_hits
		self.flinch=flinch; self.drain=drain; self.recoil=recoil; self.healing=healing
		self.ailment=ailment; self.ailment_chance=ailment_chance
		self.stat_changes=stat_changes

def _canon_stat(s: str) -> Optional[str]:
	return {"attack":"atk","defense":"def","special-attack":"sp_atk","special-defense":"sp_def","speed":"speed"}.get(s)

def _pick_frlg(move) -> Dict[str, Optional[int]]:
	try:
		for pv in getattr(move, "past_values", []) or []:
			vg = getattr(pv.version_group, "name", "")
			if vg == "firered-leafgreen":
				return {
					"accuracy": pv.accuracy if pv.accuracy is not None else move.accuracy,
					"power": pv.power if pv.power is not None else move.power,
					"pp": pv.pp if pv.pp is not None else getattr(move, "pp", None),
					"effect_chance": pv.effect_chance if pv.effect_chance is not None else getattr(move, "effect_chance", None)
				}
	except: pass
	return {"accuracy": move.accuracy, "power": move.power, "pp": getattr(move, "pp", None), "effect_chance": getattr(move, "effect_chance", None)}

def _normalize_move(move) -> MoveData:
	name = getattr(move, "name", "move").replace("-"," ").title()
	type_name = getattr(getattr(move, "type", None), "name", "normal")
	dc = getattr(getattr(move, "damage_class", None), "name", None)
	dmg_class = dc if dc in {"physical","special","status"} else ("physical" if (getattr(move,"power",0) or 0) > 0 else "status")
	pv = _pick_frlg(move)
	accuracy = pv["accuracy"]
	power = int(pv["power"] or 0)
	priority = int(getattr(move, "priority", 0) or 0)
	meta = getattr(move, "meta", None)
	min_hits = int(getattr(meta, "min_hits", 1) or 1)
	max_hits = int(getattr(meta, "max_hits", 1) or 1)
	flinch = int(getattr(meta, "flinch_chance", 0) or 0)
	drain = int(getattr(meta, "drain", 0) or 0)
	recoil = int(getattr(meta, "recoil", 0) or 0)
	healing = int(getattr(meta, "healing", 0) or 0)
	ail = getattr(getattr(meta, "ailment", None), "name", "none")
	ailment = None if ail in {None,"none","unknown"} else ail
	ailment_chance = int(getattr(meta, "ailment_chance", 0) or pv["effect_chance"] or (100 if (dmg_class=="status" and ailment) else 0) or 0)
	target_self_default = getattr(getattr(move, "target", None), "name", "") in {"user","user-or-ally","ally"}
	stat_changes = []
	try:
		for sc in getattr(move, "stat_changes", []) or []:
			raw = getattr(getattr(sc, "stat", None), "name", None)
			delta = int(getattr(sc, "change", 0) or 0)
			canon = _canon_stat(raw) if raw else None
			if canon and delta != 0:
				target_self = target_self_default if delta>0 else not target_self_default
				stat_changes.append((canon, delta, target_self))
	except: pass
	return MoveData(
		name=name, accuracy=accuracy, power=power, priority=priority, dmg_class=dmg_class, type_name=type_name,
		min_hits=min_hits, max_hits=max_hits, flinch=flinch, drain=drain, recoil=recoil, healing=healing,
		ailment=ailment, ailment_chance=ailment_chance, stat_changes=stat_changes
	)
