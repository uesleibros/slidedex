from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from .pokemon import BattlePokemon

class TargetType(Enum):
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ALLIES = "all_allies"
    ALL_ADJACENT = "all_adjacent"
    ALL_ADJACENT_FOES = "all_adjacent_foes"
    ALL = "all"
    SELF = "self"
    RANDOM_OPPONENT = "random_opponent"
    USER_OR_ALLY = "user_or_ally"

class RedirectType(Enum):
    FOLLOW_ME = "follow_me"
    RAGE_POWDER = "rage_powder"
    SPOTLIGHT = "spotlight"

class TargetingSystem:
    
    @staticmethod
    def get_redirect_target(
        allies: List[BattlePokemon],
        original_target: BattlePokemon,
        is_single_target: bool
    ) -> Optional[BattlePokemon]:
        if not is_single_target:
            return None
        
        candidates = []
        
        for pokemon in allies:
            if pokemon.fainted or pokemon == original_target:
                continue
            
            if pokemon.volatile.get("spotlight"):
                return pokemon
            
            if pokemon.volatile.get("rage_powder"):
                candidates.append((2, pokemon))
            
            if pokemon.volatile.get("follow_me"):
                candidates.append((1, pokemon))
        
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        
        return None
    
    @staticmethod
    def get_move_targets(
        attacker: BattlePokemon,
        attacker_allies: List[BattlePokemon],
        opponents: List[BattlePokemon],
        target_type: TargetType,
        selected_target: Optional[BattlePokemon] = None
    ) -> List[BattlePokemon]:
        
        if target_type == TargetType.SELF:
            return [attacker]
        
        elif target_type == TargetType.SINGLE:
            if selected_target and not selected_target.fainted:
                redirect = TargetingSystem.get_redirect_target(
                    opponents,
                    selected_target,
                    is_single_target=True
                )
                return [redirect or selected_target]
            
            alive_opponents = [p for p in opponents if not p.fainted]
            if alive_opponents:
                import random
                return [random.choice(alive_opponents)]
            return []
        
        elif target_type == TargetType.ALL_OPPONENTS:
            return [p for p in opponents if not p.fainted]
        
        elif target_type == TargetType.ALL_ALLIES:
            return [p for p in attacker_allies if not p.fainted and p != attacker]
        
        elif target_type == TargetType.ALL:
            all_pokemon = attacker_allies + opponents
            return [p for p in all_pokemon if not p.fainted]
        
        elif target_type == TargetType.USER_OR_ALLY:
            if selected_target and selected_target in attacker_allies and not selected_target.fainted:
                return [selected_target]
            return [attacker]
        
        elif target_type == TargetType.RANDOM_OPPONENT:
            alive_opponents = [p for p in opponents if not p.fainted]
            if alive_opponents:
                import random
                return [random.choice(alive_opponents)]
            return []
        
        return []
    
    @staticmethod
    def is_multi_target_move(effect_data: Dict[str, Any], move_name: str = "") -> bool:
        targets = effect_data.get("targets", "single")
        
        multi_target_types = [
            "all_opponents",
            "all_allies",
            "all_adjacent",
            "all_adjacent_foes",
            "all"
        ]
        
        if targets in multi_target_types:
            return True
        
        multi_target_moves = [
            "earthquake", "surf", "discharge", "lava_plume",
            "rock_slide", "heat_wave", "blizzard", "bulldoze",
            "dazzling_gleam", "sludge_wave", "razor_leaf",
            "icy_wind", "parabolic_charge", "self_destruct", "explosion"
        ]
        
        move_slug = move_name.lower().replace(" ", "_").replace("-", "_")
        return move_slug in multi_target_moves
    
    @staticmethod
    def can_target_ally(move_name: str, effect_data: Dict[str, Any]) -> bool:
        targets = effect_data.get("targets", "single")
        
        if targets in ["user_or_ally", "all_allies"]:
            return True
        
        ally_moves = [
            "helping_hand", "heal_pulse", "pollen_puff",
            "aromatic_mist", "bestow", "after_you"
        ]
        
        move_slug = move_name.lower().replace(" ", "_").replace("-", "_")
        return move_slug in ally_moves
    
    @staticmethod
    def get_target_type_from_effect(effect_data: Dict[str, Any]) -> TargetType:
        targets = effect_data.get("targets", "single")
        
        mapping = {
            "single": TargetType.SINGLE,
            "all_opponents": TargetType.ALL_OPPONENTS,
            "all_allies": TargetType.ALL_ALLIES,
            "all_adjacent": TargetType.ALL_ADJACENT,
            "all_adjacent_foes": TargetType.ALL_ADJACENT_FOES,
            "all": TargetType.ALL,
            "self": TargetType.SELF,
            "random_opponent": TargetType.RANDOM_OPPONENT,
            "user_or_ally": TargetType.USER_OR_ALLY
        }
        
        return mapping.get(targets, TargetType.SINGLE)


class BattleContext:
    
    def __init__(
        self,
        battle_type: str = "single",
        team1: List[BattlePokemon] = None,
        team2: List[BattlePokemon] = None
    ):
        self.battle_type = battle_type
        self.team1 = team1 or []
        self.team2 = team2 or []
    
    def is_multi_battle(self) -> bool:
        return self.battle_type in ["double", "triple", "raid", "horde"]
    
    def get_allies(self, pokemon: BattlePokemon) -> List[BattlePokemon]:
        if pokemon in self.team1:
            return [p for p in self.team1 if p != pokemon]
        elif pokemon in self.team2:
            return [p for p in self.team2 if p != pokemon]
        return []
    
    def get_opponents(self, pokemon: BattlePokemon) -> List[BattlePokemon]:
        if pokemon in self.team1:
            return self.team2
        elif pokemon in self.team2:
            return self.team1
        return []
