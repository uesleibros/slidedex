import random
from typing import Dict, Any, Optional, List
import aiopoke
from pokemon_sdk.calculations import calculate_stats
from .constants import BattleConstants, STAT_MAP
from .helpers import _apply_stage, _get_stat, _types_of

class BattlePokemon:
    __slots__ = (
        'raw', 'species_id', 'name', 'level', 'stats', 'current_hp', 
        'moves', 'pokeapi_data', 'species_data', 'is_shiny', 'stages',
        'status', 'volatile', 'sprites', 'types'
    )
    
    def __init__(self, raw: Dict[str, Any], pokeapi_data: aiopoke.Pokemon, species_data: aiopoke.PokemonSpecies):
        self.raw = raw
        self.species_id = raw["species_id"]
        self.name = raw.get("name")
        self.level = raw["level"]
        
        base_stats = raw["base_stats"]
        self.stats = calculate_stats(base_stats, raw["ivs"], raw["evs"], raw["level"], raw["nature"])
        
        current_hp = raw.get("current_hp")
        if current_hp is None:
            self.current_hp = self.stats["hp"]
        else:
            self.current_hp = max(0, min(int(current_hp), self.stats["hp"]))
        
        moves = raw.get("moves")
        if not moves:
            self.moves = [{"id": "tackle", "pp": 35, "pp_max": 35}]
        else:
            self.moves = [dict(m) for m in moves]
        
        self.pokeapi_data = pokeapi_data
        self.species_data = species_data
        self.is_shiny = raw.get("is_shiny", False)
        self.stages = {key: 0 for key in ["atk", "def", "sp_atk", "sp_def", "speed", "accuracy", "evasion"]}
        self.status = {"name": None, "counter": 0}
        self.volatile = self._init_volatile()
        self.sprites = self._init_sprites()
        self.types = _types_of(self)
    
    def _init_volatile(self) -> Dict[str, Any]:
        return {
            "flinch": False,
            "confuse": 0,
            "last_move_used": None,
            "leech_seed": False,
            "leech_seed_by": None,
            "ingrain": False,
            "substitute": 0,
            "focus_energy": False,
            "mist": 0,
            "light_screen": 0,
            "reflect": 0,
            "safeguard": 0,
            "stockpile": 0,
            "bind": 0,
            "bind_by": None,
            "trapped": False,
            "perish_count": -1,
            "encore": 0,
            "encore_move": None,
            "taunt": 0,
            "torment": False,
            "torment_last_move": None,
            "disable": 0,
            "disable_move": None,
            "yawn": 0,
            "curse": False,
            "nightmare": False,
            "destiny_bond": False,
            "grudge": False,
            "foresight": False,
            "mind_reader_target": None,
            "protect": False,
            "endure": False,
            "bide": 0,
            "bide_damage": 0,
            "rage": False,
            "rollout": 0,
            "fury_cutter": 0,
            "uproar": 0,
            "charge": False,
            "wish": 0,
            "wish_hp": 0,
            "magic_coat": False,
            "snatch": False,
            "last_damage_taken": 0,
            "last_damage_type": None
        }
    
    def _init_sprites(self) -> Dict[str, Optional[str]]:
        return {
            "front": self.pokeapi_data.sprites.front_shiny if self.is_shiny else self.pokeapi_data.sprites.front_default,
            "back": self.pokeapi_data.sprites.back_shiny if self.is_shiny else self.pokeapi_data.sprites.back_default
        }
    
    @property
    def fainted(self) -> bool:
        return self.current_hp <= 0
    
    @property
    def display_name(self) -> str:
        nickname = self.raw.get("nickname")
        if nickname:
            return nickname
        return self.name.title() if self.name else "Pokémon"
    
    @property
    def can_act(self) -> bool:
        if self.fainted:
            return False
        if self.status["name"] in ["sleep", "freeze"]:
            return False
        return True
    
    def eff_stat(self, key: str) -> int:
        val = _apply_stage(_get_stat(self.stats, key), self.stages.get(key, 0))
        if key == "speed" and self.status["name"] == "paralysis":
            val = int(val * BattleConstants.PARALYSIS_SPEED_MULT)
        return max(1, val)
    
    def dec_pp(self, move_id: str, amount: int = 1) -> bool:
        from .helpers import _slug
        slug = _slug(move_id)
        for m in self.moves:
            if _slug(m["id"]) == slug and "pp" in m:
                m["pp"] = max(0, int(m["pp"]) - amount)
                return True
        return False
    
    def get_pp(self, move_id: str) -> Optional[int]:
        from .helpers import _slug
        slug = _slug(move_id)
        for m in self.moves:
            if _slug(m["id"]) == slug:
                return int(m.get("pp", 0))
        return None
    
    def set_status(self, name: str, turns: Optional[int] = None) -> bool:
        if self.status["name"]:
            return False
        if self.volatile.get("safeguard", 0) > 0 and name in ["burn", "poison", "toxic", "paralysis", "sleep", "freeze"]:
            return False
        if self.volatile.get("substitute", 0) > 0:
            return False
        self.status = {
            "name": name,
            "counter": turns if turns is not None else (random.randint(1, 3) if name == "sleep" else 0)
        }
        return True
    
    def status_tag(self) -> str:
        from .constants import STATUS_TAGS
        tags = []
        if self.status["name"] in STATUS_TAGS:
            tags.append(STATUS_TAGS[self.status["name"]])
        if self.volatile.get("confuse", 0) > 0:
            tags.append("CNF")
        if self.volatile.get("leech_seed"):
            tags.append("SEED")
        if self.volatile.get("substitute", 0) > 0:
            tags.append("SUB")
        return f" [{'/'.join(tags)}]" if tags else ""
    
    def take_damage(self, damage: int, ignore_substitute: bool = False) -> int:
        if not ignore_substitute and self.volatile.get("substitute", 0) > 0:
            actual = min(damage, self.volatile["substitute"])
            self.volatile["substitute"] -= actual
            if self.volatile["substitute"] <= 0:
                self.volatile["substitute"] = 0
            return actual
        
        if self.volatile.get("endure") and damage >= self.current_hp and self.current_hp > 0:
            self.current_hp = 1
            return damage - 1
        
        actual = min(damage, self.current_hp)
        self.current_hp = max(0, self.current_hp - damage)
        
        if self.volatile.get("rage"):
            self.stages["atk"] = min(BattleConstants.MAX_STAT_STAGE, self.stages["atk"] + 1)
        
        if self.volatile.get("bide", 0) > 0:
            self.volatile["bide_damage"] += actual
        
        return actual
    
    def heal(self, amount: int) -> int:
        actual = min(amount, self.stats["hp"] - self.current_hp)
        self.current_hp = min(self.stats["hp"], self.current_hp + amount)
        return actual
    
    def can_switch(self) -> bool:
        if self.volatile.get("bind", 0) > 0:
            return False
        if self.volatile.get("trapped"):
            return False
        if self.volatile.get("ingrain"):
            return False
        return True
    
    def reset_stats(self) -> None:
        for key in self.stages:
            self.stages[key] = 0
    
    def clear_turn_volatiles(self) -> None:
        self.volatile.update({
            "flinch": False,
            "protect": False,
            "endure": False,
            "destiny_bond": False,
            "magic_coat": False,
            "snatch": False
        })
    
    def modify_stat_stage(self, stat: str, stages: int) -> tuple[int, int]:
        mapped_stat = STAT_MAP.get(stat, stat)
        if mapped_stat not in self.stages:
            return 0, 0
        
        if self.volatile.get("mist", 0) > 0 and stages < 0:
            return 0, 0
        
        old = self.stages[mapped_stat]
        self.stages[mapped_stat] = max(
            BattleConstants.MIN_STAT_STAGE, 
            min(BattleConstants.MAX_STAT_STAGE, self.stages[mapped_stat] + stages)
        )
        
        actual_change = self.stages[mapped_stat] - old
        return actual_change, old
    
    def get_battle_state(self) -> Dict[str, Any]:
        return {
            "current_hp": self.current_hp,
            "moves": [dict(m) for m in self.moves]
        }