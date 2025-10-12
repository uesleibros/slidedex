from sdk.constants import HAPPINESS, HAPPINESS_MIN, HAPPINESS_MAX, SOOTHE_BELL_MULTIPLIER

class HappinessService:
	@staticmethod
	def clamp(value: int) -> int:
		return max(HAPPINESS_MIN, min(HAPPINESS_MAX, value))
	
	@staticmethod
	def get_tier(current: int) -> str:
		if current < 100:
			return "low"
		elif current < 200:
			return "medium"
		return "high"
	
	@staticmethod
	def has_soothe_bell(pokemon: dict) -> bool:
		return pokemon.get("held_item") == "soothe-bell"
	
	@staticmethod
	def apply_soothe_bell(gain: int, has_bell: bool) -> int:
		if has_bell and gain > 0:
			return int(gain * SOOTHE_BELL_MULTIPLIER)
		return gain
	
	@classmethod
	def calculate_gain(cls, event_type: str, current: int, pokemon: dict) -> int:
		has_bell = cls.has_soothe_bell(pokemon)
		
		if event_type == "walk":
			gain = HAPPINESS.walk
		else:
			tier = cls.get_tier(current)
			config = getattr(HAPPINESS, event_type)
			gain = getattr(config, tier)
		
		return cls.apply_soothe_bell(gain, has_bell)
	
	@classmethod
	def calculate_loss(cls, event_type: str, current: int) -> int:
		if event_type == "faint":
			return HAPPINESS.faint
		
		tier = "high" if current >= 200 else "low"
		attr_name = f"{event_type}_{tier}"
		return getattr(HAPPINESS, attr_name)