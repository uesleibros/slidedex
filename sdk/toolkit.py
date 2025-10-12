from sdk.database import Database
from sdk.api.services import APIService
from sdk.repositories.user_repository import UserRepository
from sdk.repositories.pokemon_repository import PokemonRepository
from sdk.repositories.bag_repository import BagRepository
from sdk.services.happiness_service import HappinessService
from sdk.services.item_service import ItemService
from sdk.factories.pokemon_factory import PokemonFactory
from sdk.constants import SHINY_ROLL, STAT_KEYS, NATURES
from helpers.growth import ExperienceCalculator
from typing import Optional

class Toolkit:
	def __init__(self, path: str = "database.json"):
		self.db = Database(path)
		self.api = APIService()
		self.users = UserRepository(self.db)
		self.pokemon = PokemonRepository(self.db)
		self.bag = BagRepository(self.db)
		self.happiness = HappinessService()
		self.factory = PokemonFactory(self.api)
		self.item_service = ItemService(self.bag, self.api)
	
	def add_user(self, user_id: str, gender: str) -> dict:
		return self.users.create(user_id, gender)
	
	def get_user(self, user_id: str) -> dict:
		return self.users.get(user_id)

	def create_pokemon(
		self,
		owner_id: str,
		species_id: int,
		level: int = 5,
		**kwargs
	) -> dict:
		poke = self.api.get_pokemon(species_id)
		species = self.api.get_species(species_id)
		
		ivs = kwargs.pop("ivs", None) or self.roll_ivs(owner_id)
		nature = kwargs.pop("nature", None) or self.roll_nature(owner_id)
		ability = kwargs.pop("ability", None) or self.roll_ability(poke, owner_id)
		gender = kwargs.pop("gender", None) or self.roll_gender(owner_id, poke, species)
		is_shiny = kwargs.pop("is_shiny", None)
		
		if is_shiny is None:
			is_shiny = self.roll_shiny(owner_id)
		
		pokemon_data = self.factory.build(
			species_id=species_id,
			level=level,
			ivs=ivs,
			nature=nature,
			ability=ability,
			gender=gender,
			is_shiny=is_shiny,
			**kwargs
		)
		
		return self.pokemon.create(owner_id, pokemon_data)
	
	def add_pokemon(self, owner_id: str, **kwargs) -> dict:
		return self.pokemon.create(owner_id, kwargs)
	
	def get_pokemon(self, owner_id: str, pokemon_id: int) -> dict:
		return self.pokemon.get(owner_id, pokemon_id)

	def get_exp_for_level(self, growth_type: str, level: int) -> int:
		return ExperienceCalculator.calculate(growth_type, level)

	def get_level_from_exp(self, growth_type: str, exp: int) -> int:
		return ExperienceCalculator.get_level(growth_type, exp)

	def get_exp_progress(self, growth_type: str, current_exp: int) -> dict:
		return ExperienceCalculator.get_progress(growth_type, current_exp)
	
	def roll_random(self, user_id: str, min_val: int, max_val: int) -> int:
		rng = self.users.get_rng(user_id)
		result = rng.randint(min_val, max_val)
		self.users.save_rng(user_id, rng)
		return result
	
	def roll_chance(self, user_id: str, chance: float) -> bool:
		rng = self.users.get_rng(user_id)
		result = rng.random() < chance
		self.users.save_rng(user_id, rng)
		return result
	
	def roll_shiny(self, user_id: str) -> bool:
		return self.roll_chance(user_id, 1 / SHINY_ROLL)
	
	def roll_ivs(self, user_id: str) -> dict[str, int]:
		rng = self.users.get_rng(user_id)
		ivs = {stat: rng.randint(0, 32) for stat in STAT_KEYS}
		self.users.save_rng(user_id, rng)
		return ivs
	
	def roll_nature(self, user_id: str) -> str:
		natures = list(NATURES.keys())
		idx = self.roll_random(user_id, 0, len(natures))
		return natures[idx]
	
	def roll_ability(self, poke: dict, user_id: str) -> str:
		abilities = [
			a["ability"]["name"] 
			for a in poke.get("abilities", []) 
			if not a.get("is_hidden", False)
		]
		
		if not abilities:
			return poke["abilities"][0]["ability"]["name"]
		
		idx = self.roll_random(user_id, 0, len(abilities))
		return abilities[idx]
	
	def roll_gender(self, user_id: str, poke: Optional[dict] = None, species: Optional[dict] = None) -> str:
		if species is None and poke is not None:
			species_id = poke.get("species", {}).get("id") or poke.get("id")
			species = self.api.get_species(species_id)
		
		if species is None:
			return "Genderless"
		
		gender_rate = species.get("gender_rate", -1)
		
		if gender_rate == -1:
			return "Genderless"
		
		female_chance = gender_rate / 8.0
		return "Female" if self.roll_chance(user_id, female_chance) else "Male"