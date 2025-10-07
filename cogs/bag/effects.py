from dataclasses import dataclass
from typing import Optional, Literal, List
from pokemon_sdk.constants import EVOLUTION_STONES

@dataclass
class ItemEffect:
	type: Literal["heal", "revive", "status", "pp_restore", "pp_boost", "vitamin", 
				  "berry", "evolution", "battle_boost", "escape", "repel", "rare-candy",
				  "ev_reducer", "confusion_heal_restore", "flute", "sacred_ash"]
	amount: Optional[int] = None
	percent: Optional[float] = None
	stat: Optional[str] = None
	stages: Optional[int] = None
	cures: Optional[List[str]] = None
	cures_all: bool = False
	all_moves: bool = False
	battle_only: bool = False
	flavor: Optional[str] = None

ITEM_EFFECTS = {
	"potion": ItemEffect(type="heal", amount=20),
	"super-potion": ItemEffect(type="heal", amount=50),
	"hyper-potion": ItemEffect(type="heal", amount=200),
	"max-potion": ItemEffect(type="heal", amount=999999),
	"full-restore": ItemEffect(type="heal", amount=999999),
	"fresh-water": ItemEffect(type="heal", amount=50),
	"soda-pop": ItemEffect(type="heal", amount=60),
	"lemonade": ItemEffect(type="heal", amount=80),
	"moomoo-milk": ItemEffect(type="heal", amount=100),
	"energy-powder": ItemEffect(type="heal", amount=50),
	"energy-root": ItemEffect(type="heal", amount=200),
	"berry-juice": ItemEffect(type="heal", amount=20),
	"rare-candy": ItemEffect(type="rare-candy"),
	
	"revive": ItemEffect(type="revive", percent=0.5),
	"max-revive": ItemEffect(type="revive", percent=1.0),
	"revival-herb": ItemEffect(type="revive", percent=1.0),
	
	"antidote": ItemEffect(type="status", cures=["poison", "badly-poison"]),
	"paralyze-heal": ItemEffect(type="status", cures=["paralysis"]),
	"awakening": ItemEffect(type="status", cures=["sleep"]),
	"burn-heal": ItemEffect(type="status", cures=["burn"]),
	"ice-heal": ItemEffect(type="status", cures=["freeze"]),
	"full-heal": ItemEffect(type="status", cures_all=True),
	"heal-powder": ItemEffect(type="status", cures_all=True),
	"lava-cookie": ItemEffect(type="status", cures_all=True),
	
	"oran-berry": ItemEffect(type="berry", amount=10),
	"sitrus-berry": ItemEffect(type="berry", percent=0.25),
	"pecha-berry": ItemEffect(type="berry", cures=["poison", "badly-poison"]),
	"cheri-berry": ItemEffect(type="berry", cures=["paralysis"]),
	"chesto-berry": ItemEffect(type="berry", cures=["sleep"]),
	"rawst-berry": ItemEffect(type="berry", cures=["burn"]),
	"aspear-berry": ItemEffect(type="berry", cures=["freeze"]),
	"persim-berry": ItemEffect(type="berry", cures=["confusion"]),
	"lum-berry": ItemEffect(type="berry", cures_all=True),
	"leppa-berry": ItemEffect(type="pp_restore", amount=10),
	
	"figy-berry": ItemEffect(type="confusion_heal_restore", percent=0.125, flavor="spicy"),
	"wiki-berry": ItemEffect(type="confusion_heal_restore", percent=0.125, flavor="dry"),
	"mago-berry": ItemEffect(type="confusion_heal_restore", percent=0.125, flavor="sweet"),
	"aguav-berry": ItemEffect(type="confusion_heal_restore", percent=0.125, flavor="bitter"),
	"iapapa-berry": ItemEffect(type="confusion_heal_restore", percent=0.125, flavor="sour"),
	
	"pomeg-berry": ItemEffect(type="ev_reducer", stat="hp"),
	"kelpsy-berry": ItemEffect(type="ev_reducer", stat="attack"),
	"qualot-berry": ItemEffect(type="ev_reducer", stat="defense"),
	"hondew-berry": ItemEffect(type="ev_reducer", stat="special-attack"),
	"grepa-berry": ItemEffect(type="ev_reducer", stat="special-defense"),
	"tamato-berry": ItemEffect(type="ev_reducer", stat="speed"),
	
	"ether": ItemEffect(type="pp_restore", amount=10),
	"max-ether": ItemEffect(type="pp_restore", amount=999999),
	"elixir": ItemEffect(type="pp_restore", amount=10, all_moves=True),
	"max-elixir": ItemEffect(type="pp_restore", amount=999999, all_moves=True),
	
	"pp-up": ItemEffect(type="pp_boost", amount=1),
	"pp-max": ItemEffect(type="pp_boost", amount=3),
	
	"hp-up": ItemEffect(type="vitamin", stat="hp"),
	"protein": ItemEffect(type="vitamin", stat="attack"),
	"iron": ItemEffect(type="vitamin", stat="defense"),
	"carbos": ItemEffect(type="vitamin", stat="speed"),
	"calcium": ItemEffect(type="vitamin", stat="special-attack"),
	"zinc": ItemEffect(type="vitamin", stat="special-defense"),
	
	"x-attack": ItemEffect(type="battle_boost", stat="atk", stages=2, battle_only=True),
	"x-defense": ItemEffect(type="battle_boost", stat="def", stages=2, battle_only=True),
	"x-speed": ItemEffect(type="battle_boost", stat="speed", stages=2, battle_only=True),
	"x-accuracy": ItemEffect(type="battle_boost", stat="accuracy", stages=2, battle_only=True),
	"x-sp-atk": ItemEffect(type="battle_boost", stat="sp_atk", stages=2, battle_only=True),
	"x-sp-def": ItemEffect(type="battle_boost", stat="sp_def", stages=2, battle_only=True),
	"dire-hit": ItemEffect(type="battle_boost", stat="crit_stage", stages=2, battle_only=True),
	"guard-spec": ItemEffect(type="battle_boost", stat="guard_spec", stages=5, battle_only=True),
	
	"blue-flute": ItemEffect(type="flute", cures=["sleep"]),
	"yellow-flute": ItemEffect(type="flute", cures=["confusion"]),
	"red-flute": ItemEffect(type="flute", cures=["infatuation"]),
	
	"escape-rope": ItemEffect(type="escape"),
	"poke-doll": ItemEffect(type="escape", battle_only=True),
	"fluffy-tail": ItemEffect(type="escape", battle_only=True),
	
	"repel": ItemEffect(type="repel", amount=100),
	"super-repel": ItemEffect(type="repel", amount=200),
	"max-repel": ItemEffect(type="repel", amount=250),
	
	"sacred-ash": ItemEffect(type="sacred_ash"),
}

for stone in EVOLUTION_STONES:
	ITEM_EFFECTS[stone] = ItemEffect(type="evolution")

def get_item_effect(item_id: str) -> Optional[ItemEffect]:
	return ITEM_EFFECTS.get(item_id)

def is_consumable(item_id: str) -> bool:
	return item_id in ITEM_EFFECTS

def requires_target_pokemon(item_id: str) -> bool:
	effect = get_item_effect(item_id)
	if not effect:
		return False
	return effect.type in [
		"heal", "revive", "status", "pp_restore", "pp_boost", 
		"vitamin", "berry", "evolution", "rare-candy", "ev_reducer",
		"confusion_heal_restore", "flute"
	]