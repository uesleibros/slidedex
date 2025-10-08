import random
from typing import Dict, List, Any, Optional, Union, Tuple
from aiopoke import AiopokeClient
from aiopoke.objects.resources.evolutions.evolution_chain import EvolutionChain
from .constants import VERSION_GROUPS, SHINY_ROLL

class NoCache:
	def get(self, *_, **__): return None
	def put(self, *_, **__): return None
	def has(self, obj: Any): return False

class PokeAPIService:
	def __init__(self):
		self.client = AiopokeClient()
		self.client._cache = NoCache()

	async def get_pokemon(self, species_id: int):
		return await self.client.get_pokemon(species_id)
	
	async def get_move(self, move_id: Union[str, int]):
		return await self.client.get_move(move_id)
	
	async def get_species(self, species_id: int):
		return await self.client.get_pokemon_species(species_id)
	
	async def get_evolution_chain_safe(self, chain_id: int):
		url = f"https://pokeapi.co/api/v2/evolution-chain/{chain_id}/"
		
		response = await self.client.http.get(url)
		
		def clean_evolution_data(chain_data):
			if isinstance(chain_data, dict):
				chain_data.pop('base_form_id', None)
				
				if 'evolution_details' in chain_data:
					for detail in chain_data['evolution_details']:
						if isinstance(detail, dict):
							detail.pop('base_form_id', None)
				
				if 'evolves_to' in chain_data:
					for evo in chain_data['evolves_to']:
						clean_evolution_data(evo)
			
			return chain_data
		
		if 'chain' in data:
			data['chain'] = clean_evolution_data(data['chain'])
		
		return EvolutionChain(**data)

	def get_base_stats(self, poke) -> Dict[str, int]:
		return {s.stat.name: s.base_stat for s in poke.stats}

	def choose_ability(self, poke) -> str:
		regular = [a.ability.name for a in poke.abilities if not a.is_hidden]
		if regular:
			return random.choice(regular)
		return poke.abilities[0].ability.name

	def get_level_up_moves(self, poke, max_level: Optional[int] = None, min_level: Optional[int] = None) -> List[Tuple[str, int]]:
		moves_data = {}
		learned_move_names = set()
		
		for move_entry in poke.moves:
			best_level = None
			
			for version_detail in move_entry.version_group_details:
				if version_detail.version_group.name not in VERSION_GROUPS:
					continue
				
				if version_detail.move_learn_method.name != "level-up":
					continue
				
				learn_level = version_detail.level_learned_at
				
				if max_level is not None and learn_level > max_level:
					continue
				
				if min_level is not None and learn_level <= min_level:
					continue
				
				if best_level is None or learn_level > best_level:
					best_level = learn_level
			
			if best_level is not None:
				move_id = move_entry.move.name
				if move_id not in learned_move_names:
					moves_data[move_id] = best_level
					learned_move_names.add(move_id)
		
		result = [(move_id, level) for move_id, level in moves_data.items()]
		result.sort(key=lambda x: (x[1], x[0]))
		return result

	def select_level_up_moves(self, poke, level: int) -> List[Dict]:
		moves = self.get_level_up_moves(poke, max_level=level)
		return [{"id": move_id, "pp": 35, "pp_max": 35} for move_id, _ in moves[-4:]]

	def get_future_moves(self, poke, current_level: int) -> List[Tuple[int, str]]:
		moves = self.get_level_up_moves(poke, min_level=current_level)
		return [(level, move_id) for move_id, level in moves]

	def roll_gender(self, species, forced: Optional[str] = None) -> str:
		if forced in ("Male", "Female", "Genderless"):
			return forced
		gr = getattr(species, "gender_rate", -1)
		if gr == -1:
			return "Genderless"
		female_chance = gr * 12.5
		return "Female" if random.random() * 100 < female_chance else "Male"

	def roll_shiny(self) -> bool:
		return random.randint(1, SHINY_ROLL) == 1

	async def close(self):
		await self.client.close()


