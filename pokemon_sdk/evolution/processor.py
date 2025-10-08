from typing import Optional, Dict
import discord
from .config import EvolutionConfig, EvolutionTriggers
from .validators import EvolutionValidator, TimeManager
from .triggers import EvolutionTriggerHandler
from .messages import EvolutionMessages
from pokemon_sdk.constants import REGIONS_GENERATION

class EvolutionChainNavigator:
    @staticmethod
    def find_current_in_chain(chain_link, current_species_id: int):
        if (chain_link.species.name == str(current_species_id) or 
            chain_link.species.url.split('/')[-2] == str(current_species_id)):
            return chain_link
        
        for evo in chain_link.evolves_to:
            result = EvolutionChainNavigator.find_current_in_chain(evo, current_species_id)
            if result:
                return result
        return None

class EvolutionExecutor:
    def __init__(self, toolkit, service):
        self.tk = toolkit
        self.service = service
    
    async def evolve(self, owner_id: str, pokemon_id: int, new_species_id: int) -> Dict:
        old_pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
        
        new_poke = await self.service.get_pokemon(new_species_id)
        new_species = await self.service.get_species(new_species_id)
        new_base_stats = self.service.get_base_stats(new_poke)
        
        old_max_hp = old_pokemon["base_stats"]["hp"]
        old_current_hp = old_pokemon.get("current_hp", old_max_hp)
        hp_percent = old_current_hp / old_max_hp if old_max_hp > 0 else 1.0
        
        new_max_hp = new_base_stats["hp"]
        new_current_hp = int(new_max_hp * hp_percent)
        
        self.tk.set_level(owner_id, pokemon_id, old_pokemon["level"])
        
        updated_pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
        updated_pokemon.update({
            "species_id": new_species_id,
            "name": new_poke.name,
            "types": [t.type.name for t in new_poke.types],
            "base_stats": new_base_stats,
            "ability": self.service.choose_ability(new_poke),
            "is_legendary": new_species.is_legendary,
            "is_mythical": new_species.is_mythical,
            "growth_type": new_species.growth_rate.name,
            "region": REGIONS_GENERATION.get(new_species.generation.name, "generation-i"),
            "current_hp": new_current_hp
        })
        
        idx = self.tk._get_pokemon_index(owner_id, pokemon_id)
        self.tk.db["pokemon"][idx] = updated_pokemon
        self.tk._save()
        self.tk.set_moves(owner_id, pokemon_id, old_pokemon["moves"])
        
        del new_poke, new_species, new_base_stats
        return self.tk.get_pokemon(owner_id, pokemon_id)

class EvolutionProcessor:
    def __init__(self, toolkit, service, config: EvolutionConfig = None):
        self.tk = toolkit
        self.service = service
        self.config = config or EvolutionConfig()
        
        self.time_manager = TimeManager(self.config)
        self.validator = EvolutionValidator(self.time_manager, self.config)
        self.trigger_handler = EvolutionTriggerHandler(self.validator)
        self.executor = EvolutionExecutor(toolkit, service)
        self.navigator = EvolutionChainNavigator()
    
    async def check_evolution(
        self,
        owner_id: str,
        pokemon_id: int,
        trigger: str = EvolutionTriggers.LEVEL_UP,
        item_id: Optional[str] = None
    ) -> Optional[Dict]:
        pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
        
        if self.tk.is_evolution_blocked(owner_id, pokemon_id):
            return None
        
        species = await self.service.get_species(pokemon["species_id"])
        chain = await self.service.client.get_evolution_chain(species.evolution_chain.id)
        
        current_link = self.navigator.find_current_in_chain(chain.chain, pokemon["species_id"])
        
        if not current_link or not current_link.evolves_to:
            return None
        
        if trigger == EvolutionTriggers.LEVEL_UP:
            return await self.trigger_handler.check_level_up(
                pokemon, current_link, self.config.max_generation
            )
        elif trigger == EvolutionTriggers.USE_ITEM:
            return await self.trigger_handler.check_use_item(
                pokemon, current_link, item_id, self.config.max_generation
            )
        elif trigger == EvolutionTriggers.TRADE:
            return await self.trigger_handler.check_trade(
                pokemon, current_link, self.config.max_generation
            )
        
        return None
    
    async def evolve_pokemon(self, owner_id: str, pokemon_id: int, new_species_id: int) -> Dict:
        return await self.executor.evolve(owner_id, pokemon_id, new_species_id)
    
    def build_extra_info(self, evolution_data: Dict, pokemon: Dict) -> str:
        extra_info = ""
        
        if evolution_data.get("min_happiness"):
            extra_info += EvolutionMessages.happiness_info(
                pokemon.get('happiness', 0),
                evolution_data['min_happiness']
            )
        
        if evolution_data.get("time_of_day"):
            extra_info += EvolutionMessages.time_info(evolution_data["time_of_day"])
        
        return extra_info


