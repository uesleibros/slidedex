from typing import Optional
from .pokemon import BattlePokemon

class BallType:
	POKE_BALL = "poke-ball"
	GREAT_BALL = "great-ball"
	ULTRA_BALL = "ultra-ball"
	MASTER_BALL = "master-ball"
	SAFARI_BALL = "safari-ball"
	LEVEL_BALL = "level-ball"
	LURE_BALL = "lure-ball"
	MOON_BALL = "moon-ball"
	FRIEND_BALL = "friend-ball"
	LOVE_BALL = "love-ball"
	HEAVY_BALL = "heavy-ball"
	FAST_BALL = "fast-ball"
	SPORT_BALL = "sport-ball"
	NET_BALL = "net-ball"
	DIVE_BALL = "dive-ball"
	NEST_BALL = "nest-ball"
	REPEAT_BALL = "repeat-ball"
	TIMER_BALL = "timer-ball"
	LUXURY_BALL = "luxury-ball"
	PREMIER_BALL = "premier-ball"
	DUSK_BALL = "dusk-ball"
	HEAL_BALL = "heal-ball"
	QUICK_BALL = "quick-ball"
	CHERISH_BALL = "cherish-ball"

class PokeBallSystem:
	
	BALL_DATA = {
		BallType.POKE_BALL: {
			"name": "Poké Ball",
			"emoji": "<:pokeball:1424443006626431109>",
			"base_modifier": 1.0,
			"description": "Bola padrão para capturar Pokémon"
		},
		BallType.GREAT_BALL: {
			"name": "Great Ball",
			"emoji": "<:greatball:1424443251158552681>",
			"base_modifier": 1.5,
			"description": "Melhor que a Poké Ball padrão"
		},
		BallType.ULTRA_BALL: {
			"name": "Ultra Ball",
			"emoji": "<:ultraball:1424443441894658152>",
			"base_modifier": 2.0,
			"description": "Taxa de captura muito alta"
		},
		BallType.MASTER_BALL: {
			"name": "Master Ball",
			"emoji": "<:masterball:1424443734581317758>",
			"base_modifier": 255.0,
			"description": "Captura garantida"
		},
		BallType.SAFARI_BALL: {
			"name": "Safari Ball",
			"emoji": "<:safariball:1424443883357605938>",
			"base_modifier": 1.5,
			"description": "Usada no Safari Zone"
		},
		BallType.NET_BALL: {
			"name": "Net Ball",
			"emoji": "<:netball:1424444016505655366>",
			"base_modifier": 1.0,
			"special": "bug_water",
			"description": "3x efetiva contra Bug e Water"
		},
		BallType.NEST_BALL: {
			"name": "Nest Ball",
			"emoji": "<:nestball:1424444161570111709>",
			"base_modifier": 1.0,
			"special": "low_level",
			"description": "Melhor contra Pokémon de nível baixo"
		},
		BallType.REPEAT_BALL: {
			"name": "Repeat Ball",
			"emoji": "<:repeatball:1424444375315906660>",
			"base_modifier": 1.0,
			"special": "caught_before",
			"description": "3x se já capturou essa espécie"
		},
		BallType.TIMER_BALL: {
			"name": "Timer Ball",
			"emoji": "<:timerball:1424444622712606882>",
			"base_modifier": 1.0,
			"special": "turn_based",
			"description": "Melhor quanto mais turnos passarem"
		},
		BallType.LUXURY_BALL: {
			"name": "Luxury Ball",
			"emoji": "<:luxuryball:1424444827977650279>",
			"base_modifier": 1.0,
			"description": "Taxa normal, mas aumenta amizade"
		},
		BallType.DIVE_BALL: {
			"name": "Dive Ball",
			"emoji": "<:diveball:1424483343881474191>",
			"base_modifier": 1.0,
			"special": "underwater",
			"description": "3.5x efetiva contra Pokémon subaquáticos"
		},
		BallType.PREMIER_BALL: {
			"name": "Premier Ball",
			"emoji": "<:premierball:1424444987638022185>",
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

		elif special == "underwater":
			if location_type == "underwater":
				return base_modifier * 3.5
		
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
