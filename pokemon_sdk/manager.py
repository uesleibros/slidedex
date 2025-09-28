import random
from typing import List, Optional, Dict
from .repository import PokemonRepository
from .services import PokeAPIService
from .calculations import generate_pokemon_data, calculate_stats, iv_percent
from .constants import NATURES
from .models import Pokemon, Move

class PokemonManager:
	def __init__(self, toolkit):
		self.repo = PokemonRepository(toolkit)
		self.service = PokeAPIService()

	async def _build_pokemon_data(
		self,
		species_id: int,
		level: int = 5,
		forced_gender: Optional[str] = None,
		ivs: Optional[Dict[str,int]] = None,
		nature: Optional[str] = None,
		ability: Optional[str] = None,
		moves: Optional[List[Dict]] = None,
		shiny: Optional[bool] = None,
		held_item: Optional[str] = None,
		nickname: Optional[str] = None,
		owner_id: str = "wild",
		on_party: bool = False
	) -> Pokemon:
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

		del poke
		del species
		del base_stats
		
		return Pokemon(
			id=0,
			species_id=species_id,
			owner_id=owner_id,
			level=gen["level"],
			exp=0,
			ivs=gen["ivs"],
			evs=gen["evs"],
			nature=gen["nature"],
			ability=final_ability,
			gender=final_gender,
			is_shiny=final_shiny,
			held_item=held_item,
			caught_at="",
			moves=[Move(**m) for m in final_moves],
			stats=gen["stats"],
			current_hp=gen["current_hp"],
			on_party=on_party,
			nickname=nickname
		)

	async def generate_temp_pokemon(self, **kwargs) -> Pokemon:
		return await self._build_pokemon_data(**kwargs)

	async def create_pokemon(
		self,
		owner_id: str,
		species_id: int,
		level: int = 5,
		on_party: bool = True,
		**kwargs
	) -> Pokemon:
		pkmn = await self._build_pokemon_data(
			species_id=species_id,
			level=level,
			owner_id=owner_id,
			on_party=on_party,
			**kwargs
		)

		created = self.repo.add(
			owner_id=pkmn.owner_id,
			species_id=pkmn.species_id,
			ivs=pkmn.ivs,
			nature=pkmn.nature,
			ability=pkmn.ability,
			gender=pkmn.gender,
			shiny=pkmn.is_shiny,
			level=pkmn.level,
			moves=[m.__dict__ for m in pkmn.moves],
			on_party=pkmn.on_party,
			current_hp=pkmn.current_hp,
			held_item=pkmn.held_item,
			nickname=pkmn.nickname,
			exp=pkmn.exp
		)

		del pkmn
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

		del poke
		del base_stats
		del p
		
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


