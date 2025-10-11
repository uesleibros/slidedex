from dataclasses import dataclass
from typing import Dict

@dataclass
class EvolutionConfig:
    max_generation: int = 386
    interaction_timeout: float = 60.0
    default_timezone: str = 'America/Sao_Paulo'
    day_start_hour: int = 6
    day_end_hour: int = 18

class EvolutionTriggers:
    LEVEL_UP = "level-up"
    USE_ITEM = "use-item"
    TRADE = "trade"
    TRADE_ITEM = "trade-item"
    SHED = "shed"
    
    ALL = {LEVEL_UP, USE_ITEM, TRADE, TRADE_ITEM, SHED}
    IMPLEMENTED = {LEVEL_UP, USE_ITEM, TRADE}

class TimeOfDay:
    DAY = "day"
    NIGHT = "night"
    ANY = ""
    
    @classmethod
    def get_display_name(cls, time: str) -> str:
        return {cls.DAY: "Dia", cls.NIGHT: "Noite"}.get(time, "")

class EvolutionConditions:
    MIN_LEVEL = "min_level"
    MIN_HAPPINESS = "min_happiness"
    MIN_AFFECTION = "min_affection"
    TIME_OF_DAY = "time_of_day"
    KNOWN_MOVE = "known_move"
    HELD_ITEM = "held_item"
    ITEM = "item"
    LOCATION = "location"
    GENDER = "gender"
    
    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.MIN_LEVEL: "Nível Mínimo",
            cls.MIN_HAPPINESS: "Felicidade Mínima",
            cls.MIN_AFFECTION: "Afeição Mínima",
            cls.TIME_OF_DAY: "Período do Dia",
            cls.KNOWN_MOVE: "Movimento Necessário",
            cls.HELD_ITEM: "Item Segurado",
            cls.ITEM: "Item Necessário",
            cls.LOCATION: "Localização",
            cls.GENDER: "Gênero"
        }

class Emojis:
    EVOLUTION = "<:emojigg_Cap:1424197927496060969>"