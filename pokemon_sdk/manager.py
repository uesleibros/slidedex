import random
from typing import List, Optional, Dict
from .repository import PokemonRepository
from .services import PokeAPIService
from .calculations import generate_pokemon_data, calculate_stats, iv_percent
from .constants import NATURES
from .models import Pokemon

class PokemonManager:
	def __init__(self, toolkit):
		self.repo = PokemonRepository(toolkit)
		self.service = PokeAPIService()

	async def create_pokemon(self, owner_id: str, species_id: int, level: int = 5, forced_gender: Optional[str] = None, on_party: bool = True, ivs: Optional[Dict[str,int]] = None, nature: Optional[str] = None, ability: Optional[str] = None, moves: Optional[List[Dict]] = None, shiny: Optional[bool] = None, held_item: Optional[str] = None, nickname: Optional[str] = None) -> Pokemon:
		poke = await self.service.get_pokemon(species_id)
		species = await self.service.get_species(species_id)
		base_stats = self.service.get_base_stats(poke)
		final_ivs = ivs or {k: random.randint(0, 31) for k in base_stats.keys()}
		final_nature = nature or random.choice(list(NATURES.keys()))
		gen = generate_pokemon_data(base_stats, level=level, nature=final_nature, ivs=final_ivs)
		final_ability = ability or self.service.choose_ability(poke)
		final_moves = moves or self.service.select_level_up_moves(poke, level)
		final_gender = self.service.roll_gender(species, forced=forced_gender)
		final_shiny = shiny if shiny is not None else self.service.roll_shiny()
		created = self.repo.add(
			owner_id=owner_id,
			species_id=species_id,
			ivs=gen["ivs"],
			nature=gen["nature"],
			ability=final_ability,
			gender=final_gender,
			shiny=final_shiny,
			level=gen["level"],
			moves=final_moves,
			on_party=on_party,
			current_hp=gen["current_hp"],
			held_item=held_item,
			nickname=nickname
		)
		return created

	def get_party(self, user_id: str) -> List[Pokemon]:
		return self.repo.list(user_id, on_party=True)

	def get_box(self, user_id: str) -> List[Pokemon]:
		return self.repo.list(user_id, on_party=False)

	def list_all(self, user_id: str) -> List[Pokemon]:
		return self.repo.list(user_id, on_party=None)

	async def heal(self, owner_id: str, pokemon_id: int) -> Pokemon:
		p = self.repo.get(owner_id, pokemon_id)
		poke = await self.service.get_pokemon(p.species_id)
		base_stats = self.service.get_base_stats(poke)
		stats = calculate_stats(base_stats, p.ivs, p.evs, p.level, p.nature)
		return self.repo.set_current_hp(owner_id, pokemon_id, stats["hp"])

	def move_to_party(self, owner_id: str, pokemon_id: int) -> Pokemon:
		return self.repo.move_to_party(owner_id, pokemon_id)

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Pokemon:
		return self.repo.move_to_box(owner_id, pokemon_id)

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> Pokemon:
		return self.repo.set_moves(owner_id, pokemon_id, moves)

	def iv_percent(self, p: Pokemon, decimals: int = 2) -> float:
		return iv_percent(p.ivs, decimals)

	async def close(self):
		await self.service.close()