from typing import Optional
from sdk.api.services import APIService
from sdk.constants import REGIONS_GENERATION, STAT_KEYS
from sdk.calculations import PokemonDataGenerator
from helpers.growth import ExperienceCalculator

class PokemonFactory:
    def __init__(self, api: APIService):
        self.api = api
    
    def build(
        self,
        species_id: int,
        level: int,
        ivs: dict[str, int],
        nature: str,
        ability: str,
        gender: str,
        is_shiny: bool = False,
        held_item: Optional[str] = None,
        nickname: Optional[str] = None,
        moves: Optional[list[dict]] = None,
        on_party: bool = False,
        caught_with: str = "poke-ball"
    ) -> dict:
        poke = self.api.get_pokemon(species_id)
        species = self.api.get_species(species_id)
        base_stats = self.api.get_base_stats(poke)
        
        if moves is None:
            moves = self.api.select_level_up_moves(poke, level)
        
        data = PokemonDataGenerator.generate(
            base_stats=base_stats,
            level=level,
            nature=nature,
            ivs=ivs
        )
        
        growth_type = species["growth_rate"]["name"]
        exp = ExperienceCalculator.calculate(growth_type, level)
        
        return {
            "species_id": species_id,
            "name": poke["name"],
            "nickname": nickname,
            "level": level,
            "exp": exp,
            "ivs": ivs,
            "evs": {k: 0 for k in STAT_KEYS},
            "nature": nature,
            "ability": ability,
            "gender": gender,
            "is_shiny": is_shiny,
            "held_item": held_item,
            "types": [t["type"]["name"] for t in poke["types"]],
            "region": REGIONS_GENERATION.get(species["generation"]["name"], "Kanto"),
            "is_legendary": species.get("is_legendary", False),
            "is_mythical": species.get("is_mythical", False),
            "growth_type": growth_type,
            "happiness": species.get("base_happiness", 70),
            "base_stats": base_stats,
            "current_hp": data["current_hp"],
            "moves": moves,
            "on_party": on_party,
            "caught_with": caught_with
        }