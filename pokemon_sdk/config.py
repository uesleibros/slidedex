_instances = {}

def __getattr__(name):
	if name == 'tk':
		if 'tk' not in _instances:
			from toolkit import Toolkit
			_instances['tk'] = Toolkit()
		return _instances['tk']
	
	elif name == 'pm':
		if 'pm' not in _instances:
			from .manager import PokemonManager
			_instances['pm'] = PokemonManager()
		return _instances['pm']
	
	elif name == 'tm':
		if 'tm' not in _instances:
			from .trade.manager import TradeManager
			_instances['tm'] = TradeManager()
		return _instances['tm']
	
	elif name == 'battle_tracker':
		if 'battle_tracker' not in _instances:
			from utils.battling import BattleTracker
			_instances['battle_tracker'] = BattleTracker()
		return _instances['battle_tracker']
	
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['tk', 'pm', 'tm', 'battle_tracker']