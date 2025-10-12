import orjson
from pathlib import Path
from typing import Optional, Union, TypeAlias
from dataclasses import dataclass
import logging

Identifier: TypeAlias = Union[str, int]

@dataclass(frozen=True)
class DataPaths:
	BASE: Path = Path("data/api")
	POKEMON: Path = BASE / "pokemon.json"
	SPECIES: Path = BASE / "pokemon-species.json"
	MOVES: Path = BASE / "moves.json"
	ITEMS: Path = BASE / "items.json"
	EVOLUTION_CHAIN: Path = BASE / "evolution-chain.json"
	SPRITES: Path = BASE / "sprites"

@dataclass(frozen=True)
class SpriteVariant:
	orientation: str
	shiny: bool
	gender: Optional[str] = None
	
	def generate_filenames(self, pokemon_id: int) -> list[str]:
		id_str = str(pokemon_id).zfill(3)
		candidates = []
		
		if self.gender == "female":
			if self.shiny:
				candidates.extend([
					f"{id_str}_{self.orientation}_shiny_female.png",
					f"{id_str}_{self.orientation}_shiny.png",
					f"{id_str}_{self.orientation}_default.png"
				])
			else:
				candidates.extend([
					f"{id_str}_{self.orientation}_female.png",
					f"{id_str}_{self.orientation}_default.png"
				])
		else:
			if self.shiny:
				candidates.extend([
					f"{id_str}_{self.orientation}_shiny.png",
					f"{id_str}_{self.orientation}_default.png"
				])
			else:
				candidates.append(f"{id_str}_{self.orientation}_default.png")
		
		return candidates

class APIService:
	DEFAULT_PP = 35
	DEFAULT_MOVE_LIMIT = 4
	
	def __init__(self):
		self.logger = logging.getLogger(__name__)
	
	def get_pokemon_sprite(self, poke: dict) -> tuple[Optional[bytes], Optional[bytes]]:
		pokemon_id = int(poke["species_id"])
		gender = poke.get("gender", "").lower()
		is_shiny = poke.get("is_shiny", False)
		
		front_sprite = self._load_sprite(pokemon_id, "front", is_shiny, gender)
		back_sprite = self._load_sprite(pokemon_id, "back", is_shiny, gender)
		
		return (front_sprite, back_sprite)
	
	def _load_sprite(
		self, 
		pokemon_id: int, 
		orientation: str, 
		is_shiny: bool, 
		gender: Optional[str]
	) -> Optional[bytes]:
		variant = SpriteVariant(
			orientation=orientation,
			shiny=is_shiny,
			gender=gender if gender == "female" else None
		)
		
		for filename in variant.generate_filenames(pokemon_id):
			sprite_path = DataPaths.SPRITES / filename
			if sprite_path.exists():
				return sprite_path.read_bytes()
		
		return None
	
	def get_pokemon(self, identifier: Identifier) -> Optional[dict]:
		pokemon_list = self._load_json(DataPaths.POKEMON)
		return self._find_by_identifier(pokemon_list, identifier)
	
	def get_move(self, identifier: Identifier) -> Optional[dict]:
		moves_list = self._load_json(DataPaths.MOVES)
		return self._find_by_identifier(moves_list, identifier)
	
	def get_item(self, identifier: Identifier) -> Optional[dict]:
		items_list = self._load_json(DataPaths.ITEMS)
		return self._find_by_identifier(items_list, identifier)
	
	def get_species(self, species_id: int) -> Optional[dict]:
		species_list = self._load_json(DataPaths.SPECIES)
		
		for species in species_list:
			if species.get("id") == species_id:
				self._inject_evolution_chain_id(species)
				return species
		
		return None
	
	def get_all_species(self, start: int = 1, end: int = 386) -> list[dict]:
		species_list = self._load_json(DataPaths.SPECIES)
		results = []
		
		for species in species_list:
			species_id = species.get("id")
			if species_id and start <= species_id <= end:
				self._inject_evolution_chain_id(species)
				results.append(species)
		
		return results
	
	def get_evolution_chain(self, chain_id: int) -> Optional[dict]:
		chains = self._load_json(DataPaths.EVOLUTION_CHAIN)
		
		for chain in chains:
			if chain.get("id") == chain_id:
				return chain
		
		return None
	
	def get_base_stats(self, poke: dict) -> dict[str, int]:
		return {stat["stat"]["name"]: stat["base_stat"] for stat in poke["stats"]}
	
	def get_level_up_moves(
		self, 
		poke: dict, 
		max_level: Optional[int] = None, 
		min_level: Optional[int] = None
	) -> list[tuple[str, int]]:
		moves_data = {}
		
		for move_entry in poke["moves"]:
			if move_entry["move_learn_method"] != "level-up":
				continue
			
			level = move_entry.get("level_learned_at", 0)
			
			if max_level is not None and level > max_level:
				continue
			
			if min_level is not None and level <= min_level:
				continue
			
			move_name = move_entry["name"]
			if move_name not in moves_data or level > moves_data[move_name]:
				moves_data[move_name] = level
		
		return sorted(moves_data.items(), key=lambda x: (x[1], x[0]))
	
	def select_level_up_moves(self, poke: dict, level: int) -> list[dict]:
		last_moves = self.get_level_up_moves(poke, max_level=level)[-self.DEFAULT_MOVE_LIMIT:]
		
		if not last_moves:
			return []
		
		return [self._create_move_data(move_name) for move_name, _ in last_moves]
	
	def get_future_moves(self, poke: dict, current_level: int) -> list[tuple[int, str]]:
		moves = self.get_level_up_moves(poke, min_level=current_level)
		return [(level, move_name) for move_name, level in moves]
	
	def _create_move_data(self, move_name: str) -> dict:
		move = self.get_move(move_name)
		pp = move["pp"] if move else self.DEFAULT_PP
		
		return {
			"id": move_name,
			"pp": pp,
			"pp_max": pp
		}
	
	def _find_by_identifier(self, data_list: list[dict], identifier: Identifier) -> Optional[dict]:
		is_numeric = isinstance(identifier, int) or str(identifier).isdigit()
		search_value = int(identifier) if is_numeric else str(identifier).lower()
		search_key = "id" if is_numeric else "name"
		
		for item in data_list:
			if item.get(search_key) == search_value:
				return item
		
		return None
	
	def _inject_evolution_chain_id(self, species: dict) -> None:
		if "evolution_chain" in species and "url" in species["evolution_chain"]:
			chain_id = self._extract_id_from_url(species["evolution_chain"]["url"])
			species["evolution_chain"]["id"] = chain_id
	
	@staticmethod
	def _load_json(path: Path) -> list[dict]:
		with open(path, "rb") as f:
			return orjson.loads(f.read())
	
	@staticmethod
	def _extract_id_from_url(url: str) -> int:
		return int(url.rstrip('/').split('/')[-1])