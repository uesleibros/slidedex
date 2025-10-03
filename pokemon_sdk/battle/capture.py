import math
import random
from typing import Tuple
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .pokeballs import PokeBallSystem, BallType

class CaptureSystem:
	
	@staticmethod
	def attempt_capture_gen3(
		wild: BattlePokemon,
		ball_type: str = BallType.POKE_BALL,
		turn: int = 1,
		time_of_day: str = "day",
		location_type: str = "normal",
		already_caught: bool = False
	) -> Tuple[bool, int, float]:
		max_hp = wild.stats["hp"]
		cur_hp = max(1, wild.current_hp)
		
		capture_rate = int(getattr(wild.species_data, "capture_rate", 45) or 45)
		
		ball_modifier = PokeBallSystem.calculate_modifier(
			ball_type=ball_type,
			wild=wild,
			turn=turn,
			time_of_day=time_of_day,
			location_type=location_type,
			already_caught=already_caught
		)
		
		status = wild.status["name"]
		status_bonus = BattleConstants.SLEEP_STATUS_BONUS if status in {"sleep", "freeze"} else (
			BattleConstants.PARA_STATUS_BONUS if status in {"paralysis", "poison", "burn", "toxic"} else 1.0
		)
		
		a = int(((3 * max_hp - 2 * cur_hp) * capture_rate * ball_modifier * status_bonus) / (3 * max_hp))
		
		if a >= BattleConstants.CAPTURE_MAX_VALUE:
			return True, 4, ball_modifier
		if a <= 0:
			return False, 0, ball_modifier
		
		shake_probability = int(1048560 / math.sqrt(math.sqrt((16711680 / a))))
		shakes = 0
		
		for _ in range(4):
			if random.randint(0, BattleConstants.CAPTURE_RANGE - 1) < shake_probability:
				shakes += 1
			else:
				break
		
		return shakes == 4, shakes, ball_modifier
	
	@staticmethod
	def get_catch_rate_percentage(
		wild: BattlePokemon,
		ball_type: str = BallType.POKE_BALL,
		turn: int = 1,
		time_of_day: str = "day",
		location_type: str = "normal",
		already_caught: bool = False
	) -> float:
		max_hp = wild.stats["hp"]
		cur_hp = max(1, wild.current_hp)
		
		capture_rate = int(getattr(wild.species_data, "capture_rate", 45) or 45)
		
		ball_modifier = PokeBallSystem.calculate_modifier(
			ball_type=ball_type,
			wild=wild,
			turn=turn,
			time_of_day=time_of_day,
			location_type=location_type,
			already_caught=already_caught
		)
		
		status = wild.status["name"]
		status_bonus = BattleConstants.SLEEP_STATUS_BONUS if status in {"sleep", "freeze"} else (
			BattleConstants.PARA_STATUS_BONUS if status in {"paralysis", "poison", "burn", "toxic"} else 1.0
		)
		
		a = ((3 * max_hp - 2 * cur_hp) * capture_rate * ball_modifier * status_bonus) / (3 * max_hp)
		
		if a >= BattleConstants.CAPTURE_MAX_VALUE:
			return 100.0
		
		catch_rate = (a / BattleConstants.CAPTURE_MAX_VALUE) * 100
		return min(100.0, max(0.0, catch_rate))
