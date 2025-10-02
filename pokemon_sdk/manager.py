import random
import aiopoke
from typing import List, Optional, Dict
from .repository import PokemonRepository
from .services import PokeAPIService
from .calculations import generate_pokemon_data, calculate_stats, iv_percent
from .constants import NATURES, REGIONS_GENERATION

class PokemonManager:
	def __init__(self, toolkit):
		self.repo = PokemonRepository(toolkit)
		self.service = PokeAPIService()

	async def _build_pokemon_data(
		self,
		species_id: int,
		level: int = 5,
		forced_gender: Optional[str] = None,
		ivs: Optional[Dict[str, int]] = None,
		nature: Optional[str] = None,
		ability: Optional[str] = None,
		moves: Optional[List[Dict]] = None,
		shiny: Optional[bool] = None,
		held_item: Optional[str] = None,
		nickname: Optional[str] = None,
		owner_id: str = "wild",
		on_party: bool = False
	) -> Dict:
		poke: aiopoke.Pokemon = await self.service.get_pokemon(species_id)
		species: aiopoke.PokemonSpecies = await self.service.get_species(species_id)
		base_stats = self.service.get_base_stats(poke)

		pkm_name = poke.name

		final_ivs = ivs or {k: random.randint(0, 31) for k in base_stats.keys()}
		final_nature = nature or random.choice(list(NATURES.keys()))

		is_legendary: bool = species.is_legendary
		is_mythical: bool = species.is_mythical
		poke_types: list = [x.type.name for x in poke.types]
		poke_region: str = REGIONS_GENERATION.get(species.generation.name, "generation-i")

		gen = generate_pokemon_data(base_stats, level=level, nature=final_nature, ivs=final_ivs)
		final_ability = ability or self.service.choose_ability(poke)
		final_moves = moves or self.service.select_level_up_moves(poke, level)
		final_gender = self.service.roll_gender(species, forced=forced_gender)
		final_shiny = shiny if shiny is not None else self.service.roll_shiny()

		del poke
		del species
		del base_stats

		return {
			"id": 0,
			"species_id": species_id,
			"owner_id": owner_id,
			"level": gen["level"],
			"exp": 0,
			"ivs": gen["ivs"],
			"evs": gen["evs"],
			"nature": gen["nature"],
			"ability": final_ability,
			"gender": final_gender,
			"is_shiny": final_shiny,
			"held_item": held_item,
			"caught_at": "",
			"types": poke_types,
			"region": poke_region,
			"is_legendary": is_legendary,
			"is_mythical": is_mythical,
			"moves": final_moves,
			"base_stats": gen["stats"],
			"current_hp": gen["current_hp"],
			"on_party": on_party,
			"nickname": nickname,
			"name": pkm_name
		}

	async def generate_temp_pokemon(self, **kwargs) -> Dict:
		return await self._build_pokemon_data(**kwargs)

	async def create_pokemon(
		self,
		owner_id: str,
		species_id: int,
		level: int = 5,
		on_party: bool = True,
		**kwargs
	) -> Dict:
		pkmn = await self._build_pokemon_data(
			species_id=species_id,
			level=level,
			owner_id=owner_id,
			on_party=on_party,
			**kwargs
		)

		created = self.repo.add(
			owner_id=pkmn["owner_id"],
			species_id=pkmn["species_id"],
			ivs=pkmn["ivs"],
			nature=pkmn["nature"],
			ability=pkmn["ability"],
			gender=pkmn["gender"],
			shiny=pkmn["is_shiny"],
			level=pkmn["level"],
			moves=pkmn["moves"],
			is_legendary=pkmn["is_legendary"],
			is_mythical=pkmn["is_mythical"],
			types=pkmn["types"],
			region=pkmn["region"],
			on_party=pkmn["on_party"],
			current_hp=pkmn["current_hp"],
			held_item=pkmn["held_item"],
			nickname=pkmn["nickname"],
			base_stats=pkmn["base_stats"],
			name=pkmn["name"],
			exp=pkmn["exp"]
		)

		return created
		
	async def process_level_up(
		self,
		owner_id: str,
		pokemon_id: int,
		levels_gained: List[int]
	) -> Dict:
		if not levels_gained:
			return {
				"learned": [],
				"pending": [],
				"levels_gained": []
			}
		
		pokemon = self.repo.get(owner_id, pokemon_id)
		poke: aiopoke.Pokemon = await self.service.get_pokemon(pokemon["species_id"])
		
		new_moves_data = {}
		
		for move_entry in poke.moves:
			for version_detail in move_entry.version_group_details:
				if version_detail.move_learn_method.name == "level-up":
					learn_level = version_detail.level_learned_at
					if learn_level in levels_gained:
						move_id = move_entry.move.name
						if move_id not in new_moves_data:
							new_moves_data[move_id] = {
								"level": learn_level,
								"move_entry": move_entry
							}
		
		learned = []
		pending = []
		
		sorted_moves = sorted(new_moves_data.items(), key=lambda x: x[1]["level"])
		
		for move_id, move_data in sorted_moves:
			if self.repo.has_move(owner_id, pokemon_id, move_id):
				continue
			
			try:
				move_detail = await self.service.get_move(move_id)
				pp_max = move_detail.pp if move_detail.pp else 10
			except:
				pp_max = 10
			
			if self.repo.tk.can_learn_move(owner_id, pokemon_id):
				self.repo.tk.learn_move(owner_id, pokemon_id, move_id, pp_max)
				learned.append({
					"id": move_id,
					"name": move_id.replace("-", " ").title(),
					"level": move_data["level"],
					"pp_max": pp_max
				})
			else:
				self.repo.tk.add_pending_move(owner_id, pokemon_id, move_id)
				pending.append({
					"id": move_id,
					"name": move_id.replace("-", " ").title(),
					"level": move_data["level"]
				})
		
		del poke
		
		return {
			"learned": learned,
			"pending": pending,
			"levels_gained": levels_gained
		}
		
	def get_party(self, user_id: str) -> List[Dict]:
		return self.repo.list(user_id, on_party=True)

	def get_box(self, user_id: str) -> List[Dict]:
		return self.repo.list(user_id, on_party=False)

	def list_all(self, user_id: str) -> List[Dict]:
		return self.repo.list(user_id, on_party=None)

	async def heal(self, owner_id: str, pokemon_id: int) -> Dict:
		p = self.repo.get(owner_id, pokemon_id)  # dict
		poke = await self.service.get_pokemon(p["species_id"])
		base_stats = self.service.get_base_stats(poke)
		stats = calculate_stats(base_stats, p["ivs"], p["evs"], p["level"], p["nature"])

		del poke
		del base_stats
		del p

		return self.repo.set_current_hp(owner_id, pokemon_id, stats["hp"])

	def move_to_party(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.repo.move_to_party(owner_id, pokemon_id)

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.repo.move_to_box(owner_id, pokemon_id)

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> Dict:
		return self.repo.set_moves(owner_id, pokemon_id, moves)

	def iv_percent(self, p: Dict, decimals: int = 2) -> float:
		return iv_percent(p["ivs"], decimals)

	async def close(self):

		await self.service.close()

