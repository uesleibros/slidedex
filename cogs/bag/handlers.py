from typing import Dict, Optional, List, Tuple
from pokemon_sdk.calculations import calculate_max_hp
from .effects import get_item_effect

class ItemHandler:
	def __init__(self, toolkit, pm):
		self.toolkit = toolkit
		self.pm = pm
	
	def use_healing_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type not in ["heal", "berry"]:
			raise ValueError("Item não é curativo")
		
		max_hp = calculate_max_hp(
			pokemon["base_stats"]["hp"],
			pokemon["ivs"]["hp"],
			pokemon["evs"]["hp"],
			pokemon["level"]
		)
		current_hp = pokemon.get("current_hp", max_hp)
		
		if current_hp >= max_hp:
			raise ValueError("HP já está cheio")
		
		if current_hp <= 0:
			raise ValueError("Pokémon está desmaiado. Use um Revive")
		
		if effect.amount:
			heal_amount = effect.amount
		elif effect.percent:
			heal_amount = int(max_hp * effect.percent)
		else:
			raise ValueError("Efeito de cura inválido")
		
		new_hp = min(current_hp + heal_amount, max_hp)
		healed = new_hp - current_hp
		
		self.toolkit.set_current_hp(uid, pokemon_id, new_hp)
		self.toolkit.remove_item(uid, item_id, 1)
		
		if item_id in ["energy-powder", "energy-root"]:
			if item_id == "energy-powder":
				self.toolkit.decrease_happiness_energy_powder(uid, pokemon_id)
			else:
				self.toolkit.decrease_happiness_energy_root(uid, pokemon_id)
		elif effect.type == "berry":
			self.toolkit.increase_happiness_berry(uid, pokemon_id)
		
		return {
			"healed": healed,
			"current_hp": new_hp,
			"max_hp": max_hp
		}
	
	def use_revive_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type != "revive":
			raise ValueError("Item não é revive")
		
		current_hp = pokemon.get("current_hp", 1)
		if current_hp > 0:
			raise ValueError("Pokémon não está desmaiado")
		
		max_hp = calculate_max_hp(
			pokemon["base_stats"]["hp"],
			pokemon["ivs"]["hp"],
			pokemon["evs"]["hp"],
			pokemon["level"]
		)
		
		restored_hp = int(max_hp * effect.percent)
		
		self.toolkit.set_current_hp(uid, pokemon_id, restored_hp)
		self.toolkit.clear_pokemon_status(uid, pokemon_id)
		self.toolkit.remove_item(uid, item_id, 1)
		
		if item_id == "revival-herb":
			self.toolkit.decrease_happiness_revival_herb(uid, pokemon_id)
		
		return {
			"restored_hp": restored_hp,
			"max_hp": max_hp
		}
	
	def use_status_heal_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type != "status_heal":
			raise ValueError("Item não cura status")
		
		current_status = pokemon.get("status", {}).get("name")
		
		if not current_status:
			raise ValueError("Pokémon não está com status alterado")
		
		if current_status == "fainted":
			raise ValueError("Pokémon está desmaiado. Use um Revive")
		
		if effect.cures_all or current_status in effect.cures:
			self.toolkit.clear_pokemon_status(uid, pokemon_id)
			self.toolkit.remove_item(uid, item_id, 1)
			
			if item_id == "heal-powder":
				self.toolkit.decrease_happiness_heal_powder(uid, pokemon_id)
			
			return {
				"cured_status": current_status,
				"item_used": item_id
			}
		else:
			raise ValueError(f"Este item não cura {current_status}")
	
	def use_pp_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict, move_slot: Optional[int] = None) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type not in ["pp_restore", "pp_boost"]:
			raise ValueError("Item não restaura PP")
		
		moves = pokemon.get("moves", [])
		if not moves:
			raise ValueError("Pokémon não tem movimentos")
		
		if effect.type == "pp_restore":
			updated = False
			for move in moves:
				if effect.all_moves or move["pp"] < move["pp_max"]:
					if effect.amount == -1:
						move["pp"] = move["pp_max"]
					else:
						move["pp"] = min(move["pp"] + effect.amount, move["pp_max"])
					updated = True
			
			if not updated:
				raise ValueError("PP já está no máximo")
			
			self.toolkit.set_moves(uid, pokemon_id, moves)
			self.toolkit.remove_item(uid, item_id, 1)
			
			return {"moves": moves}
		
		elif effect.type == "pp_boost":
			if len(moves) == 1:
				move_idx = 0
			elif move_slot and 1 <= move_slot <= len(moves):
				move_idx = move_slot - 1
			else:
				raise ValueError(f"Especifique o slot do movimento (1-{len(moves)})")
			
			move = moves[move_idx]
			current_pp_ups = move.get("pp_ups", 0)
			
			if item_id == "pp-max":
				if current_pp_ups >= 3:
					raise ValueError("Movimento já está no máximo de PP Ups")
				needed_ups = 3 - current_pp_ups
				boost_amount = (move["pp_max"] // 5) * needed_ups
				move["pp_max"] += boost_amount
				move["pp"] = min(move["pp"] + boost_amount, move["pp_max"])
				move["pp_ups"] = 3
			else:
				if current_pp_ups >= 3:
					raise ValueError("Movimento já está no máximo de PP Ups")
				boost_amount = move["pp_max"] // 5
				move["pp_max"] += boost_amount
				move["pp"] = min(move["pp"] + boost_amount, move["pp_max"])
				move["pp_ups"] = current_pp_ups + 1
			
			self.toolkit.set_moves(uid, pokemon_id, moves)
			self.toolkit.remove_item(uid, item_id, 1)
			
			return {"move": move, "move_name": move["id"]}
	
	def use_vitamin(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type != "vitamin":
			raise ValueError("Item não é vitamina")
		
		current_evs = pokemon.get("evs", {})
		current_stat_ev = current_evs.get(effect.stat, 0)
		
		if current_stat_ev >= 100:
			raise ValueError(f"Limite de EVs (100) atingido para {effect.stat}")
		
		total_evs = sum(current_evs.values())
		if total_evs >= 510:
			raise ValueError("Limite total de EVs (510) atingido")
		
		ev_gain = min(10, 100 - current_stat_ev, 510 - total_evs)
		
		new_evs = current_evs.copy()
		new_evs[effect.stat] = current_stat_ev + ev_gain
		
		self.toolkit.set_evs(uid, pokemon_id, new_evs)
		self.toolkit.remove_item(uid, item_id, 1)
		self.toolkit.increase_happiness_vitamin(uid, pokemon_id)
		
		return {
			"stat": effect.stat,
			"ev_gain": ev_gain,
			"new_ev": new_evs[effect.stat],
			"total_evs": sum(new_evs.values())
		}
	
	def use_ev_reducing_berry(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type != "ev_reducer":
			raise ValueError("Item não reduz EVs")
		
		current_evs = pokemon.get("evs", {})
		current_stat_ev = current_evs.get(effect.stat, 0)
		
		if current_stat_ev == 0:
			raise ValueError(f"Pokémon não tem EVs em {effect.stat}")
		
		new_stat_ev = max(0, current_stat_ev - 10)
		
		new_evs = current_evs.copy()
		new_evs[effect.stat] = new_stat_ev
		
		self.toolkit.set_evs(uid, pokemon_id, new_evs)
		self.toolkit.remove_item(uid, item_id, 1)
		self.toolkit.increase_happiness_berry(uid, pokemon_id)
		
		return {
			"stat": effect.stat,
			"ev_reduced": current_stat_ev - new_stat_ev,
			"new_ev": new_stat_ev,
			"total_evs": sum(new_evs.values())
		}
	
	def use_evolution_stone(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Optional[Dict]:
		evolution_data = self.pm.check_evolution(uid, pokemon_id, trigger="use-item", item_id=item_id)
		
		if not evolution_data or evolution_data.get("item") != item_id:
			raise ValueError("Pokémon não pode evoluir com este item")
		
		self.toolkit.remove_item(uid, item_id, 1)
		evolved = self.pm.evolve_pokemon(uid, pokemon_id, evolution_data["species_id"])
		
		return {"evolved": evolved, "from_species": pokemon["species_id"]}
	
	def use_flute(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type != "flute":
			raise ValueError("Item não é uma flauta")
		
		current_status = pokemon.get("status", {}).get("name")
		
		if not current_status:
			raise ValueError("Pokémon não está com status alterado")
		
		if current_status in effect.cures:
			self.toolkit.clear_pokemon_status(uid, pokemon_id)
			return {
				"cured_status": current_status,
				"item_used": item_id
			}
		else:
			raise ValueError(f"Esta flauta não cura {current_status}")
	
	def use_sacred_ash(self, uid: str) -> Dict:
		party = self.toolkit.get_user_party(uid)
		
		if not party:
			raise ValueError("Você não tem Pokémon no party")
		
		fainted_pokemon = [p for p in party if p.get("current_hp", 1) <= 0]
		
		if not fainted_pokemon:
			raise ValueError("Nenhum Pokémon está desmaiado")
		
		revived = []
		
		for pokemon in fainted_pokemon:
			max_hp = calculate_max_hp(
				pokemon["base_stats"]["hp"],
				pokemon["ivs"]["hp"],
				pokemon["evs"]["hp"],
				pokemon["level"]
			)
			
			self.toolkit.set_current_hp(uid, pokemon["id"], max_hp)
			self.toolkit.clear_pokemon_status(uid, pokemon["id"])
			self.toolkit.restore_pp(uid, pokemon["id"])
			
			revived.append({
				"pokemon_id": pokemon["id"],
				"name": pokemon.get("name", "Unknown"),
				"restored_hp": max_hp
			})
		
		self.toolkit.remove_item(uid, "sacred-ash", 1)
		
		return {
			"revived_count": len(revived),
			"revived_pokemon": revived
		}
	
	def use_confusion_berry(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
		effect = get_item_effect(item_id)
		if not effect or effect.type != "confusion_heal_restore":
			raise ValueError("Item não é berry de cura com restauração")
		
		max_hp = calculate_max_hp(
			pokemon["base_stats"]["hp"],
			pokemon["ivs"]["hp"],
			pokemon["evs"]["hp"],
			pokemon["level"]
		)
		current_hp = pokemon.get("current_hp", max_hp)
		
		if current_hp <= 0:
			raise ValueError("Pokémon está desmaiado")
		
		if current_hp >= max_hp:
			raise ValueError("HP já está cheio")
		
		heal_amount = int(max_hp * effect.percent)
		new_hp = min(current_hp + heal_amount, max_hp)
		healed = new_hp - current_hp
		
		self.toolkit.set_current_hp(uid, pokemon_id, new_hp)
		self.toolkit.remove_item(uid, item_id, 1)
		self.toolkit.increase_happiness_berry(uid, pokemon_id)
		
		nature = pokemon.get("nature", "")
		likes_flavor = effect.flavor in self._get_liked_flavors(nature)
		
		confusion_applied = False
		if not likes_flavor:
			self.toolkit.set_status(uid, pokemon_id, "confusion", 0)
			confusion_applied = True
		
		return {
			"healed": healed,
			"current_hp": new_hp,
			"max_hp": max_hp,
			"confusion_applied": confusion_applied
		}
	
	def _get_liked_flavors(self, nature: str) -> List[str]:
		NATURE_FLAVORS = {
			"lonely": ["spicy"],
			"brave": ["spicy"],
			"adamant": ["spicy"],
			"naughty": ["spicy"],
			"bold": ["sour"],
			"relaxed": ["sour"],
			"impish": ["sour"],
			"lax": ["sour"],
			"timid": ["sweet"],
			"hasty": ["sweet"],
			"jolly": ["sweet"],
			"naive": ["sweet"],
			"modest": ["dry"],
			"mild": ["dry"],
			"quiet": ["dry"],
			"rash": ["dry"],
			"calm": ["bitter"],
			"gentle": ["bitter"],
			"sassy": ["bitter"],
			"careful": ["bitter"],
			"hardy": [],
			"docile": [],
			"serious": [],
			"bashful": [],
			"quirky": []
		}
		
		return NATURE_FLAVORS.get(nature.lower(), [])