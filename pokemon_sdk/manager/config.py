from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class UIConfig:
    interaction_timeout: float = 60.0
    max_moves: int = 4
    
@dataclass
class GameConfig:
    default_level: int = 5
    min_level: int = 1
    max_level: int = 100
    max_generation: int = 386
    default_timezone: str = 'America/Sao_Paulo'
    default_language: str = 'en'
    day_start_hour: int = 6
    day_end_hour: int = 18
    level_reward_interval: int = 10
    
@dataclass
class StatusConfig:
    default_status: Dict = None
    
    def __post_init__(self):
        if self.default_status is None:
            self.default_status = {"name": None, "counter": 0}

class ItemPool:
    RANDOM_ITEMS = [
        "potion", "super-potion", "hyper-potion", "full-heal",
        "revive", "antidote", "paralyze-heal", "awakening",
        "burn-heal", "ice-heal", "poke-ball", "great-ball",
        "ultra-ball", "rare-candy", "protein", "iron",
        "carbos", "calcium", "hp-up", "zinc", "pp-up", "pp-max"
    ]
    
    LEVEL_REWARDS = {
        10: [("potion", 3)],
        20: [("super-potion", 2), ("poke-ball", 5)],
        30: [("hyper-potion", 2), ("great-ball", 3)],
        40: [("full-heal", 2), ("ultra-ball", 2)],
        50: [("max-potion", 1), ("rare-candy", 1)],
        60: [("full-restore", 2), ("pp-up", 1)],
        70: [("max-revive", 2), ("protein", 1)],
        80: [("full-restore", 3), ("rare-candy", 2)],
        90: [("max-elixir", 2), ("pp-max", 1)],
        100: [("master-ball", 1), ("rare-candy", 5)]
    }
    
    CAPTURE_REWARDS_BASE = [("poke-ball", (1, 3))]
    CAPTURE_REWARDS_SHINY = [
        ("rare-candy", (1, 2)),
        ("ultra-ball", (2, 5))
    ]
    CAPTURE_REWARDS_LEGENDARY = [
        ("master-ball", 1),
        ("rare-candy", 5),
        ("max-revive", 3)
    ]
    CAPTURE_REWARDS_MYTHICAL = [
        ("master-ball", 2),
        ("rare-candy", 10),
        ("pp-max", 3)
    ]

class ItemCategories:
    MAPPING = {
        "stat-boosts": "items",
        "medicine": "items",
        "other": "items",
        "vitamins": "items",
        "healing": "items",
        "pp-recovery": "items",
        "revival": "items",
        "status-cures": "items",
        "loot": "items",
        "held-items": "items",
        "choice": "items",
        "effort-drop": "items",
        "bad-held-items": "items",
        "training": "items",
        "plates": "items",
        "species-specific": "items",
        "type-enhancement": "items",
        "event-items": "key_items",
        "gameplay": "key_items",
        "plot-advancement": "key_items",
        "unused": "key_items",
        "standard-balls": "pokeballs",
        "special-balls": "pokeballs",
        "apricorn-balls": "pokeballs",
        "all-machines": "tms_hms",
        "tm": "tms_hms",
        "hm": "tms_hms",
        "berries": "berries"
    }
    
    BERRY_SUFFIX = "-berry"
    DEFAULT_CATEGORY = "items"

class Emojis:
    EVOLUTION = "<:emojigg_Cap:1424197927496060969>"
    LEVEL_UP = "<:Cuck:1424197273235095616>"