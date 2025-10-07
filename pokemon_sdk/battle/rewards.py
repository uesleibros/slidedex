from typing import List, Dict, Optional, Tuple
from .pokemon import BattlePokemon
from utils.formatting import format_pokemon_display

class BattleRewards:
	
	@staticmethod
	def calculate_ev_yield(defeated_pokemon: BattlePokemon) -> Dict[str, int]:
		base_stats = defeated_pokemon.raw.get("base_stats", {})
		ev_yield = {}
		
		stats_map = {
			"hp": "hp",
			"attack": "attack",
			"defense": "defense",
			"special-attack": "special-attack",
			"special-defense": "special-defense",
			"speed": "speed"
		}
		
		for stat_key, stat_name in stats_map.items():
			base_value = base_stats.get(stat_key, 0)
			
			if base_value >= 120:
				ev_yield[stat_name] = 3
			elif base_value >= 100:
				ev_yield[stat_name] = 2
			elif base_value >= 70:
				ev_yield[stat_name] = 1
			else:
				ev_yield[stat_name] = 0
		
		total_evs = sum(ev_yield.values())
		if total_evs == 0:
			highest_stat = max(stats_map.keys(), key=lambda k: base_stats.get(k, 0))
			ev_yield[stats_map[highest_stat]] = 1
		
		return ev_yield
	
	@staticmethod
	def calculate_base_experience(
		defeated_pokemon: BattlePokemon,
		is_trainer_battle: bool = False
	) -> int:
		base_experience = defeated_pokemon.pokeapi_data.base_experience if defeated_pokemon.pokeapi_data.base_experience else 50
		enemy_level = defeated_pokemon.level
		
		base_exp_gain = int((base_experience * enemy_level) / 7)
		
		if is_trainer_battle:
			base_exp_gain = int(base_exp_gain * 1.5)
		
		return base_exp_gain
	
	@staticmethod
	def apply_exp_modifiers(
		base_exp: int,
		participant_count: int,
		has_lucky_egg: bool = False,
		is_traded: bool = False,
		has_exp_share: bool = False
	) -> int:
		exp_to_give = base_exp // max(1, participant_count)
		
		if has_lucky_egg:
			exp_to_give = int(exp_to_give * 1.5)
		
		if is_traded:
			exp_to_give = int(exp_to_give * 1.5)
		
		if has_exp_share:
			exp_to_give = int(exp_to_give * 1.5)
		
		return max(1, exp_to_give)
	
	@staticmethod
	def apply_ev_modifiers(
		base_evs: Dict[str, int],
		has_macho_brace: bool = False,
		has_power_item: Optional[str] = None
	) -> Dict[str, int]:
		modified_evs = base_evs.copy()
		
		if has_macho_brace:
			modified_evs = {k: v * 2 for k, v in modified_evs.items()}
		
		if has_power_item:
			power_items_map = {
				"power_weight": "hp",
				"power_bracer": "attack",
				"power_belt": "defense",
				"power_lens": "special-attack",
				"power_band": "special-defense",
				"power_anklet": "speed"
			}
			
			if has_power_item in power_items_map:
				stat = power_items_map[has_power_item]
				modified_evs[stat] = modified_evs.get(stat, 0) + 4
		
		return modified_evs
	
	@staticmethod
	def format_experience_gains(
		distribution: List[Tuple[int, str, int]],
		max_level_count: int = 0
	) -> List[str]:
		lines = []
		
		if not distribution:
			if max_level_count > 0:
				lines.append(f"ℹ️ Todos os Pokémon estão no nível máximo (não ganharam XP)")
			return lines
		
		if len(distribution) > 1:
			lines.append(f"**EXP Distribuído** ({len(distribution)} participantes):")
		else:
			lines.append("**EXP Ganho:**")
		
		for index, pokemon, experience in distribution:
			lines.append(f"  • {format_pokemon_display(pokemon.raw, bold_name=False, show_gender=False, show_item=False, show_fav=False, show_status=False)} +{experience} XP")
		
		if max_level_count > 0:
			lines.append("")
			lines.append(f"ℹ️ {max_level_count} Pokémon no nível máximo (não ganhou XP)")
		
		return lines