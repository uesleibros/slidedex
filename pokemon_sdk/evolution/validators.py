from typing import Dict, Optional, Any
from datetime import datetime
import pytz
from .config import EvolutionConfig, TimeOfDay

class TimeManager:
    def __init__(self, config: EvolutionConfig = None):
        self.config = config or EvolutionConfig()
        self.timezone = pytz.timezone(self.config.default_timezone)
    
    def get_time_of_day(self) -> str:
        current_time = datetime.now(self.timezone)
        hour = current_time.hour
        
        if self.config.day_start_hour <= hour < self.config.day_end_hour:
            return TimeOfDay.DAY
        return TimeOfDay.NIGHT

class EvolutionValidator:
    def __init__(self, time_manager: TimeManager = None, config: EvolutionConfig = None):
        self.time_manager = time_manager or TimeManager()
        self.config = config or EvolutionConfig()
    
    def validate_generation(self, species_id: int) -> bool:
        return species_id <= self.config.max_generation
    
    def validate_trigger(self, detail_trigger: str, expected_trigger: str) -> bool:
        return detail_trigger == expected_trigger
    
    def validate_level(self, pokemon_level: int, min_level: Optional[int]) -> bool:
        if not min_level:
            return True
        return pokemon_level >= min_level
    
    def validate_happiness(self, current: int, required: Optional[int]) -> bool:
        if not required:
            return True
        return current >= required
    
    def validate_affection(self, current: int, required: Optional[int]) -> bool:
        if not required:
            return True
        return current >= required
    
    def validate_time_of_day(self, required: Optional[str]) -> bool:
        if not required or required in [TimeOfDay.ANY, None]:
            return True
        current = self.time_manager.get_time_of_day()
        return current == required
    
    def validate_known_move(self, pokemon_moves: list, required_move: Optional[str]) -> bool:
        if not required_move:
            return True
        return any(move.get("id") == required_move for move in pokemon_moves)
    
    def validate_held_item(self, pokemon_item: Optional[str], required_item: Optional[str]) -> bool:
        if not required_item:
            return True
        return pokemon_item == required_item
    
    def validate_item(self, item_id: Optional[str], required_item: Optional[str]) -> bool:
        if not required_item:
            return True
        return item_id == required_item
    
    def validate_all_conditions(
        self,
        pokemon: Dict,
        detail: Any,
        trigger: str,
        item_id: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        if detail.trigger.name != trigger:
            return False, "Trigger incorreto"
        
        if trigger == "level-up":
            if not self.validate_level(pokemon["level"], detail.min_level):
                return False, f"Nível mínimo {detail.min_level} necessário"
            
            if not self.validate_happiness(pokemon.get("happiness", 0), detail.min_happiness):
                return False, f"Felicidade {detail.min_happiness} necessária"
            
            if not self.validate_affection(pokemon.get("happiness", 0), detail.min_affection):
                return False, f"Afeição {detail.min_affection} necessária"
            
            if not self.validate_time_of_day(detail.time_of_day):
                return False, f"Período do dia incorreto"
            
            if not self.validate_known_move(pokemon.get("moves", []), detail.known_move.name if detail.known_move else None):
                return False, f"Movimento {detail.known_move.name} necessário"
        
        elif trigger == "use-item":
            if not self.validate_item(item_id, detail.item.name if detail.item else None):
                return False, f"Item {detail.item.name} necessário"
        
        elif trigger == "trade":
            if not self.validate_held_item(pokemon.get("held_item"), detail.held_item.name if detail.held_item else None):
                return False, f"Item {detail.held_item.name} deve estar sendo segurado"
        
        return True, None
