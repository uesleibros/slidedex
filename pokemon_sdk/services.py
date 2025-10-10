import random
import orjson
from typing import Dict, List, Optional, Union, Tuple, Any
from munch import Munch, munchify
from .constants import SHINY_ROLL
import logging
import os

class PokeAPIService:
	def __init__(self):
		self.logger = logging.getLogger(__name__)

	@staticmethod
	def _extract_id_from_url(url: str) -> int:
		return int(url.rstrip('/').split('/')[-1])

	def get_pokemon_sprite(self, poke: Dict[str, Any]) -> Tuple[Optional[bytes], Optional[bytes]]:
		id_str = str(int(poke["species_id"])).zfill(3)
		
		def find_sprite(orientation: str) -> Optional[bytes]:
			candidates = []
			if poke["gender"].lower() == "female":
				if poke["is_shiny"]:
					candidates.extend([
						f"{id_str}_{orientation}_shiny_female.png",
						f"{id_str}_{orientation}_shiny.png",
						f"{id_str}_{orientation}_default.png"
					])
				else:
					candidates.extend([
						f"{id_str}_{orientation}_female.png",
						f"{id_str}_{orientation}_default.png"
					])
			else:
				if poke["is_shiny"]:
					candidates.extend([
						f"{id_str}_{orientation}_shiny.png",
						f"{id_str}_{orientation}_default.png"
					])
				else:
					candidates.append(f"{id_str}_{orientation}_default.png")

			for name in candidates:
				path = os.path.join("data/api/sprites", name)
				if os.path.exists(path):
					with open(path, "rb") as f:
						return f.read()
			return None
		
		return (find_sprite("front"), find_sprite("back"))

	def get_pokemon(self, identifier: Union[str, int]) -> Optional[Munch]:
		is_id = isinstance(identifier, int) or str(identifier).isdigit()
		search_identifier = str(identifier).lower() if not is_id else int(identifier)
		try:
			with open("data/api/pokemon.json", "r", encoding="utf-8") as f:
				data = orjson.loads(f.read())
			for poke in data:
				if (is_id and poke.get("id") == search_identifier) or (not is_id and poke.get("name") == search_identifier):
					return munchify(poke)
		except Exception as e:
			self.logger.error(f"Erro ao ler pokemon.json: {e}")
		return None

	def get_move(self, move_id: Union[str, int]) -> Optional[Munch]:
		is_id = isinstance(move_id, int) or str(move_id).isdigit()
		search_id = int(move_id) if is_id else str(move_id).lower()
		try:
			with open("data/api/moves.json", "r", encoding="utf-8") as f:
				data = orjson.loads(f.read())
			for move in data:
				if (is_id and move.get("id") == search_id) or (not is_id and move.get("name") == search_id):
					return munchify(move)
		except Exception as e:
			self.logger.error(f"Erro ao ler moves.json: {e}")
		return None

	def get_all_species(self, start: int = 1, end: int = 386) -> List[Munch]:
		results = []
		try:
			with open("data/api/pokemon-species.json", "r", encoding="utf-8") as f:
				data = orjson.loads(f.read())
			for specie in data:
				sid = specie.get("id")
				if sid and start <= sid <= end:
					if "evolution_chain" in specie and "url" in specie["evolution_chain"]:
						chain_id = self._extract_id_from_url(specie["evolution_chain"]["url"])
						specie["evolution_chain"]["id"] = chain_id
					results.append(munchify(specie))
		except Exception as e:
			self.logger.error(f"Erro ao ler pokemon-species.json: {e}")
		return results

	def get_species(self, species_id: int) -> Optional[Munch]:
		try:
			with open("data/api/pokemon-species.json", "r", encoding="utf-8") as f:
				data = orjson.loads(f.read())
			for specie in data:
				if specie.get("id") == species_id:
					if "evolution_chain" in specie and "url" in specie["evolution_chain"]:
						chain_id = self._extract_id_from_url(specie["evolution_chain"]["url"])
						specie["evolution_chain"]["id"] = chain_id
					return munchify(specie)
		except Exception as e:
			self.logger.error(f"Erro ao ler pokemon-species.json: {e}")
		return None

	def get_evolution_chain(self, chain_id: int) -> Optional[Munch]:
		try:
			with open("data/api/evolution-chain.json", "r", encoding="utf-8") as f:
				data = orjson.loads(f.read())
			for chain in data:
				if chain.get("id") == chain_id:
					return munchify(chain)
		except Exception as e:
			self.logger.error(f"Erro ao ler evolution-chain.json: {e}")
		return None

	def get_item(self, identifier: Union[str, int]) -> Optional[Munch]:
		is_id = isinstance(identifier, int) or str(identifier).isdigit()
		search_identifier = int(identifier) if is_id else str(identifier).lower()
		try:
			with open("data/api/items.json", "r", encoding="utf-8") as f:
				data = orjson.loads(f.read())
			for item in data:
				if (is_id and item.get("id") == search_identifier) or (not is_id and item.get("name") == search_identifier):
					return munchify(item)
		except Exception as e:
			self.logger.error(f"Erro ao ler items.json: {e}")
		return None

	@staticmethod
	def get_base_stats(poke) -> Dict[str, int]:
		return {s.stat.name: s.base_stat for s in poke.stats}

	@staticmethod
	def choose_ability(poke) -> str:
		regular = [a.ability.name for a in poke.abilities if not a.is_hidden]
		return random.choice(regular) if regular else poke.abilities[0].ability.name

	@staticmethod
	def get_level_up_moves(poke, max_level: Optional[int] = None, min_level: Optional[int] = None) -> List[Tuple[str, int]]:
		moves_data = {}
		for move_entry in poke.moves:
			if move_entry.move_learn_method != "level-up":
				continue
			level_learned = move_entry.level_learned_at or 0
			if max_level is not None and level_learned > max_level:
				continue
			if min_level is not None and level_learned <= min_level:
				continue
			if move_entry.name not in moves_data or level_learned > moves_data[move_entry.name]:
				moves_data[move_entry.name] = level_learned
		return sorted(moves_data.items(), key=lambda x: (x[1], x[0]))

	def select_level_up_moves(self, poke, level: int) -> List[Dict]:
		last_moves = self.get_level_up_moves(poke, max_level=level)[-4:]
		if not last_moves:
			return []
		move_data_list = [self.get_move(mid) for mid, _ in last_moves]
		return [{"id": mid, "pp": (md.pp if md else 35), "pp_max": (md.pp if md else 35)} for (mid, _), md in zip(last_moves, move_data_list)]

	def get_future_moves(self, poke, current_level: int) -> List[Tuple[int, str]]:
		moves = self.get_level_up_moves(poke, min_level=current_level)
		return [(lvl, mid) for mid, lvl in moves]

	@staticmethod
	def roll_gender(species, forced: Optional[str] = None) -> str:
		if forced in ("Male", "Female", "Genderless"):
			return forced
		gr = getattr(species, "gender_rate", -1)
		if gr == -1:
			return "Genderless"
		return "Female" if random.random() * 100 < gr * 12.5 else "Male"

	@staticmethod
	def roll_shiny() -> bool:
		return random.randint(1, SHINY_ROLL) == 1