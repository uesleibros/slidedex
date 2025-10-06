from dataclasses import dataclass
from typing import Optional, Literal, Callable
from pokemon_sdk.constants import EVOLUTION_STONES

@dataclass
class ItemEffect:
    type: Literal["heal", "revive", "status", "pp_restore", "pp_boost", "vitamin", 
                  "berry", "evolution", "battle_boost", "escape", "repel", "rare-candy"]
    amount: Optional[int] = None
    percent: Optional[float] = None
    stat: Optional[str] = None
    stages: Optional[int] = None
    cures: Optional[str] = None
    all_moves: bool = False
    battle_only: bool = False

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
    
    "antidote": ItemEffect(type="status", cures="poison"),
    "paralyz-heal": ItemEffect(type="status", cures="paralysis"),
    "awakening": ItemEffect(type="status", cures="sleep"),
    "burn-heal": ItemEffect(type="status", cures="burn"),
    "ice-heal": ItemEffect(type="status", cures="freeze"),
    "full-heal": ItemEffect(type="status", cures="all"),
    
    "oran-berry": ItemEffect(type="berry", amount=10),
    "sitrus-berry": ItemEffect(type="berry", percent=0.25),
    "pecha-berry": ItemEffect(type="status", cures="poison"),
    "cheri-berry": ItemEffect(type="status", cures="paralysis"),
    "chesto-berry": ItemEffect(type="status", cures="sleep"),
    "rawst-berry": ItemEffect(type="status", cures="burn"),
    "aspear-berry": ItemEffect(type="status", cures="freeze"),
    "persim-berry": ItemEffect(type="status", cures="confusion"),
    "lum-berry": ItemEffect(type="status", cures="all"),
    "leppa-berry": ItemEffect(type="pp_restore", amount=10),
    
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
    
    "escape-rope": ItemEffect(type="escape", battle_only=True),
    "poke-doll": ItemEffect(type="escape", battle_only=True),
    "fluffy-tail": ItemEffect(type="escape", battle_only=True),
    
    "repel": ItemEffect(type="repel", amount=100),
    "super-repel": ItemEffect(type="repel", amount=200),
    "max-repel": ItemEffect(type="repel", amount=250),
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
    return effect.type in ["heal", "revive", "status", "pp_restore", "pp_boost", "vitamin", "berry", "evolution"]
