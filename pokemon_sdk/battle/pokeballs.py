from typing import Optional
from .pokemon import BattlePokemon

class BallType:
    POKE_BALL = "poke_ball"
    GREAT_BALL = "great_ball"
    ULTRA_BALL = "ultra_ball"
    MASTER_BALL = "master_ball"
    SAFARI_BALL = "safari_ball"
    LEVEL_BALL = "level_ball"
    LURE_BALL = "lure_ball"
    MOON_BALL = "moon_ball"
    FRIEND_BALL = "friend_ball"
    LOVE_BALL = "love_ball"
    HEAVY_BALL = "heavy_ball"
    FAST_BALL = "fast_ball"
    SPORT_BALL = "sport_ball"
    NET_BALL = "net_ball"
    DIVE_BALL = "dive_ball"
    NEST_BALL = "nest_ball"
    REPEAT_BALL = "repeat_ball"
    TIMER_BALL = "timer_ball"
    LUXURY_BALL = "luxury_ball"
    PREMIER_BALL = "premier_ball"
    DUSK_BALL = "dusk_ball"
    HEAL_BALL = "heal_ball"
    QUICK_BALL = "quick_ball"
    CHERISH_BALL = "cherish_ball"

class PokeBallSystem:
    
    BALL_DATA = {
        BallType.POKE_BALL: {
            "name": "Poké Ball",
            "emoji": "<:pokeball_pixel:1423036002855026719>",
            "base_modifier": 1.0,
            "description": "Bola padrão para capturar Pokémon"
        },
        BallType.GREAT_BALL: {
            "name": "Great Ball",
            "emoji": "<:greatball_pixel:1423036220161659023>",
            "base_modifier": 1.5,
            "description": "Melhor que a Poké Ball padrão"
        },
        BallType.ULTRA_BALL: {
            "name": "Ultra Ball",
            "emoji": "<:ultraball_pixel:1423036299949903904>",
            "base_modifier": 2.0,
            "description": "Taxa de captura muito alta"
        },
        BallType.MASTER_BALL: {
            "name": "Master Ball",
            "emoji": "<:masterball_pixel:1423036370875715607>",
            "base_modifier": 255.0,
            "description": "Captura garantida"
        },
        BallType.SAFARI_BALL: {
            "name": "Safari Ball",
            "emoji": "<:safariball_pixel:1423036598211055769>",
            "base_modifier": 1.5,
            "description": "Usada no Safari Zone"
        },
        BallType.NET_BALL: {
            "name": "Net Ball",
            "emoji": "<:netball_pixel:1423036752687403018>",
            "base_modifier": 1.0,
            "special": "bug_water",
            "description": "3x efetiva contra Bug e Water"
        },
        BallType.NEST_BALL: {
            "name": "Nest Ball",
            "emoji": "<:nestball_pixel:1423036884992659537>",
            "base_modifier": 1.0,
            "special": "low_level",
            "description": "Melhor contra Pokémon de nível baixo"
        },
        BallType.REPEAT_BALL: {
            "name": "Repeat Ball",
            "emoji": "<:repeatball_pixel:1423036444896919665>",
            "base_modifier": 1.0,
            "special": "caught_before",
            "description": "3x se já capturou essa espécie"
        },
        BallType.TIMER_BALL: {
            "name": "Timer Ball",
            "emoji": "<:timerball_pixel:1423036514769829991>",
            "base_modifier": 1.0,
            "special": "turn_based",
            "description": "Melhor quanto mais turnos passarem"
        },
        BallType.LUXURY_BALL: {
            "name": "Luxury Ball",
            "emoji": "<:luxuryball_pixel:1423037034809004105>",
            "base_modifier": 1.0,
            "description": "Taxa normal, mas aumenta amizade"
        },
        BallType.PREMIER_BALL: {
            "name": "Premier Ball",
            "emoji": "<:premierball_pixel:1423036684391415880>",
            "base_modifier": 1.0,
            "description": "Taxa igual à Poké Ball"
        },
    }
    
    @classmethod
    def calculate_modifier(
        cls,
        ball_type: str,
        wild: BattlePokemon,
        turn: int = 1,
        time_of_day: str = "day",
        location_type: str = "normal",
        already_caught: bool = False
    ) -> float:
        if ball_type not in cls.BALL_DATA:
            ball_type = BallType.POKE_BALL
        
        ball_info = cls.BALL_DATA[ball_type]
        base_modifier = ball_info["base_modifier"]
        
        if ball_type == BallType.MASTER_BALL:
            return 255.0
        
        special = ball_info.get("special")
        
        if special == "bug_water":
            if any(t in ["bug", "water"] for t in wild.types):
                return base_modifier * 3.0
        
        elif special == "low_level":
            if wild.level <= 20:
                modifier = (41 - wild.level) / 10
                return max(1.0, modifier)
            return 1.0
        
        elif special == "caught_before":
            if already_caught:
                return base_modifier * 3.0
        
        elif special == "turn_based":
            multiplier = min(4.0, 1.0 + (turn - 1) * 0.3)
            return base_modifier * multiplier
        
        elif special == "night_cave":
            if time_of_day in ["night", "dusk"] or location_type == "cave":
                return base_modifier * 3.5
        
        elif special == "first_turn":
            if turn == 1:
                return base_modifier * 5.0
            return base_modifier
        
        elif special == "underwater":
            if location_type == "underwater":
                return base_modifier * 3.5
        
        return base_modifier
    
    @classmethod
    def get_ball_emoji(cls, ball_type: str) -> str:
        return cls.BALL_DATA.get(ball_type, cls.BALL_DATA[BallType.POKE_BALL])["emoji"]
    
    @classmethod
    def get_ball_name(cls, ball_type: str) -> str:
        return cls.BALL_DATA.get(ball_type, cls.BALL_DATA[BallType.POKE_BALL])["name"]
    
    @classmethod
    def get_all_balls(cls):
        return cls.BALL_DATA
