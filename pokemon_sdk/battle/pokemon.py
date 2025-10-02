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
            "last_damage_type": None,
            "attracted": False,
            "attracted_to": None,
            "imprison": False,
            "imprisoned_moves": [],
            "helping_hand": False,
            "transformed": False,
            "transformed_into": None,
            "original_types": None,
            "original_ability": None,
            "copied_ability": None,
            "mud_sport_active": False,
            "water_sport_active": False,
            "minimized": False,
            "defense_curl": False,
            "flash_fire": False,
            "identified": False,
            "last_item_used": None,
            "received_item": None,
            "given_item": None,
            "used_item": None,
            "embargo": 0,
            "heal_block": 0,
            "aqua_ring": False,
            "magnet_rise": 0,
            "telekinesis": 0,
            "miracle_eye": False,
            "follow_me": False,
            "powder": False,
            "electrify": False,
            "charging": False,
            "semi_invulnerable": False,
            "two_turn_move": None,
            "locked_move": None,
            "locked_turns": 0,
            "must_recharge": False,
            "focus_punch_setup": False,
            "beak_blast_setup": False,
            "shell_trap_setup": False,
            "fury_cutter_count": 0,
            "rollout_count": 0,
            "ice_ball_count": 0,
            "defense_curl_used": False,
            "minimize_used": False,
            "roost_used": False,
            "metronome_count": 0,
            "last_move_hit": False,
            "last_move_failed": False,
            "stall_counter": 0,
            "protect_count": 0,
            "baneful_bunker": False,
            "kings_shield": False,
            "spiky_shield": False,
            "crafty_shield": False,
            "mat_block": False,
            "quick_guard": False,
            "wide_guard": False
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
        if self.volatile.get("attracted"):
            tags.append("❤️")
        if self.volatile.get("trapped"):
            tags.append("TRAP")
        if self.volatile.get("transformed"):
            tags.append("COPY")
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
        
        self.volatile["last_damage_taken"] = actual
        
        return actual
    
    def heal(self, amount: int) -> int:
        if self.volatile.get("heal_block", 0) > 0:
            return 0
        
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
        if self.volatile.get("encore", 0) > 0:
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
            "snatch": False,
            "helping_hand": False,
            "follow_me": False,
            "focus_punch_setup": False,
            "beak_blast_setup": False,
            "shell_trap_setup": False,
            "baneful_bunker": False,
            "kings_shield": False,
            "spiky_shield": False,
            "mat_block": False
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
            "moves": [dict(m) for m in self.moves],
            "status": dict(self.status),
            "stages": dict(self.stages),
            "volatile_keys": {k: v for k, v in self.volatile.items() if v and k not in ["leech_seed_by", "bind_by", "attracted_to", "mind_reader_target", "transformed_into"]}
        }
    
    def is_move_disabled(self, move_id: str) -> bool:
        from .helpers import _slug
        slug = _slug(move_id)
        
        if self.volatile.get("disable", 0) > 0:
            disabled_move = self.volatile.get("disable_move")
            if disabled_move and _slug(disabled_move) == slug:
                return True
        
        if self.volatile.get("encore", 0) > 0:
            encore_move = self.volatile.get("encore_move")
            if encore_move and _slug(encore_move) != slug:
                return True
        
        if self.volatile.get("taunt", 0) > 0:
            return True
        
        if self.volatile.get("imprison"):
            imprisoned = self.volatile.get("imprisoned_moves", [])
            if slug in imprisoned:
                return True
        
        if self.volatile.get("torment"):
            last = self.volatile.get("torment_last_move")
            if last and _slug(last) == slug:
                return True
        
        return False
    
    def can_use_item(self) -> bool:
        if self.volatile.get("embargo", 0) > 0:
            return False
        return True
    
    def is_semi_invulnerable(self) -> bool:
        return self.volatile.get("semi_invulnerable", False)
    
    def get_effective_types(self) -> List[str]:
        if self.volatile.get("transformed") and self.volatile.get("transformed_into"):
            target = self.volatile["transformed_into"]
            return target.types.copy() if hasattr(target, 'types') else self.types.copy()
        
        original_types = self.volatile.get("original_types")
        if original_types:
            return original_types.copy()
        
        return self.types.copy()
    
    def reset_volatiles(self) -> None:
        self.volatile = self._init_volatile()
    
    def copy_stat_changes(self, other: 'BattlePokemon') -> None:
        for stat in self.stages:
            self.stages[stat] = other.stages[stat]
