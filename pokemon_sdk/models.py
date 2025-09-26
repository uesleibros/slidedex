from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class Move:
	id: str
	pp: int
	pp_max: int

@dataclass
class Pokemon:
	id: int
	species_id: int
	owner_id: str
	level: int
	exp: int
	ivs: Dict[str, int]
	evs: Dict[str, int]
	nature: str
	ability: str
	gender: str
	is_shiny: bool
	held_item: Optional[str]
	caught_at: str
	moves: List[Move] = field(default_factory=list)
	stats: Dict[str, int] = field(default_factory=dict)
	current_hp: int = 0
	on_party: bool = False
	nickname: Optional[str] = None

	@staticmethod
	def from_dict(d: Dict) -> "Pokemon":
		mv = [Move(**m) for m in d.get("moves", [])]
		return Pokemon(
			id=int(d["id"]),
			species_id=int(d["species_id"]),
			owner_id=d["owner_id"],
			level=int(d["level"]),
			exp=int(d.get("exp", 0)),
			ivs=d["ivs"],
			evs=d.get("evs", {k:0 for k in ("hp","attack","defense","special-attack","special-defense","speed")}),
			nature=d["nature"],
			ability=d["ability"],
			gender=d.get("gender","Genderless"),
			is_shiny=bool(d.get("is_shiny", False)),
			held_item=d.get("held_item"),
			caught_at=d.get("caught_at",""),
			moves=mv,
			stats=d.get("stats", {}),
			current_hp=int(d.get("current_hp", 0) if d.get("current_hp") is not None else 0),
			on_party=bool(d.get("on_party", False)),
			nickname=d.get("nickname")
		)