from typing import Optional
from sdk.repositories.pokemon_repository import PokemonRepository
from sdk.constants import HELD_ITEM_EFFECTS, MAX_LEVEL
from helpers.growth import GrowthRate

class ExperienceService:
    def __init__(self, pokemon_repo: PokemonRepository):
        self.pokemon = pokemon_repo
    
    def add(self, owner_id: str, pokemon_id: int, exp_gain: int) -> dict:
        pokemon = self.pokemon.get(owner_id, pokemon_id)
        
        modified_exp = self._apply_lucky_egg(pokemon, exp_gain)
        
        old_level = pokemon["level"]
        growth_type = pokemon["growth_type"]
        
        new_exp = min(
            pokemon["exp"] + modified_exp,
            GrowthRate.calculate_exp(growth_type, MAX_LEVEL)
        )
        
        new_level = min(
            GrowthRate.get_level_from_exp(growth_type, new_exp),
            MAX_LEVEL
        )
        
        levels_gained = list(range(old_level + 1, new_level + 1)) if new_level > old_level else []
        
        updates = {
            "exp": new_exp,
            "level": new_level
        }
        
        if levels_gained:
            updates["current_hp"] = self._calculate_hp_on_level(pokemon, new_level)
        
        self.pokemon.update(owner_id, pokemon_id, updates)
        
        return {
            "old_level": old_level,
            "new_level": new_level,
            "levels_gained": levels_gained,
            "exp_gain": modified_exp,
            "lucky_egg_bonus": modified_exp - exp_gain,
            "max_level_reached": new_level >= MAX_LEVEL
        }
    
    def _apply_lucky_egg(self, pokemon: dict, exp_gain: int) -> int:
        if pokemon.get("held_item") == "lucky-egg":
            multiplier = HELD_ITEM_EFFECTS["lucky-egg"]["exp_multiplier"]
            return int(exp_gain * multiplier)
        return exp_gain
    
    def _calculate_hp_on_level(self, pokemon: dict, new_level: int) -> int:
        from pokemon_sdk.calculations import calculate_max_hp
        
        return calculate_max_hp(
            pokemon["base_stats"]["hp"],
            pokemon["ivs"]["hp"],
            pokemon["evs"]["hp"],
            new_level
        )