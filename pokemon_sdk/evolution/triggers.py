from typing import Optional, Dict, Any
from .validators import EvolutionValidator
from .config import EvolutionTriggers

class EvolutionTriggerHandler:
    def __init__(self, validator: EvolutionValidator):
        self.validator = validator
    
    def check_level_up(
        self,
        pokemon: Dict,
        evolution_link: Any,
        max_generation: int
    ) -> Optional[Dict]:
        for evolution in evolution_link.evolves_to:
            evolution_species_id = int(evolution.species.url.split('/')[-2])
            
            if not self.validator.validate_generation(evolution_species_id):
                continue
            
            for detail in evolution.evolution_details:
                valid, reason = self.validator.validate_all_conditions(
                    pokemon, detail, EvolutionTriggers.LEVEL_UP
                )
                
                if valid:
                    return self._build_evolution_data(evolution, detail, evolution_species_id)
        
        return None
    
    def check_use_item(
        self,
        pokemon: Dict,
        evolution_link: Any,
        item_id: str,
        max_generation: int
    ) -> Optional[Dict]:
        for evolution in evolution_link.evolves_to:
            evolution_species_id = int(evolution.species.url.split('/')[-2])
            
            if not self.validator.validate_generation(evolution_species_id):
                continue
            
            for detail in evolution.evolution_details:
                valid, reason = self.validator.validate_all_conditions(
                    pokemon, detail, EvolutionTriggers.USE_ITEM, item_id
                )
                
                if valid:
                    return self._build_evolution_data(evolution, detail, evolution_species_id)
        
        return None
    
    def check_trade(
        self,
        pokemon: Dict,
        evolution_link: Any,
        max_generation: int
    ) -> Optional[Dict]:
        for evolution in evolution_link.evolves_to:
            evolution_species_id = int(evolution.species.url.split('/')[-2])
            
            if not self.validator.validate_generation(evolution_species_id):
                continue
            
            for detail in evolution.evolution_details:
                valid, reason = self.validator.validate_all_conditions(
                    pokemon, detail, EvolutionTriggers.TRADE
                )
                
                if valid:
                    return self._build_evolution_data(evolution, detail, evolution_species_id)
        
        return None
    
    def _build_evolution_data(self, evolution: Any, detail: Any, species_id: int) -> Dict:
        return {
            "species_id": species_id,
            "name": evolution.species.name.title(),
            "trigger": detail.trigger.name,
            "min_level": detail.min_level if detail.min_level else None,
            "item": detail.item.name if detail.item else None,
            "min_happiness": detail.min_happiness if detail.min_happiness else None,
            "min_affection": detail.min_affection if detail.min_affection else None,
            "known_move": detail.known_move.name if detail.known_move else None,
            "held_item": detail.held_item.name if detail.held_item else None,
            "time_of_day": detail.time_of_day if detail.time_of_day else None
        }