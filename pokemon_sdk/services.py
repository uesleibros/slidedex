import random
from typing import Dict, List, Optional, Union, Tuple
from munch import Munch, munchify
from .constants import SHINY_ROLL
from curl_cffi.requests import AsyncSession
import logging
import ijson
import gc

class PokeAPIService:
	def __init__(self):
		self._BASE_URL: str = "https://pokeapi.co/api/v2"
		self._session: Optional[AsyncSession] = None
		self.logger = logging.getLogger(__name__)
	
	async def __aenter__(self):
		if not self._session:
			self._session = AsyncSession(
				timeout=30,
				impersonate="chrome110",
				max_clients=10
			)
		return self
	
	async def __aexit__(self, exc_type, exc_val, exc_tb):
		await self.close()
	
	async def close(self):
		if self._session:
			await self._session.close()
			self._session = None
		gc.collect()
	
	def _ensure_session(self):
		if not self._session:
			self._session = AsyncSession(
				timeout=30,
				impersonate="chrome110",
				max_clients=10
			)
	
	async def _request(self, endpoint: str) -> Munch:
		self._ensure_session()
		url = f"{self._BASE_URL}/{endpoint}"
		
		try:
			resp = await self._session.get(url)
			resp.raise_for_status()
			data = munchify(resp.json())
			del resp
			return data
		except Exception as e:
			self.logger.error(f"Erro ao buscar {url}: {str(e)}")
			raise
		finally:
			gc.collect()

	async def get_bytes(self, url: str) -> bytes:
		self._ensure_session()
		try:
			resp = await self._session.get(url)
			resp.raise_for_status()
			content = resp.content
			del resp
			return content
		except Exception as e:
			self.logger.error(f"Erro ao ler {url}: {str(e)}")
			raise
		finally:
			gc.collect()

	@staticmethod
	def _extract_id_from_url(url: str) -> int:
		return int(url.rstrip('/').split('/')[-1])

	async def get_pokemon(self, identifier: Union[str, int]) -> Munch:
		is_id = isinstance(identifier, int) or str(identifier).isdigit()
		if not is_id:
			identifier = str(identifier).lower()
		try:
			with open("data/api/pokemon.json", "r") as f:
				parser = ijson.items(f, "item")
				for poke in parser:
					if is_id:
						if poke.get("id") == int(identifier):
							result = poke
							del poke
							gc.collect()
							return munchify(result)
					else:
						if poke.get("name") == identifier:
							result = poke
							del poke
							gc.collect()
							return munchify(result)
		except Exception as e:
			self.logger.error(f"Erro ao ler pokemon.json: {e}")
			return None
		finally:
			gc.collect()
		return None
	
	async def get_move(self, move_id: Union[str, int]) -> Munch:
		is_id = isinstance(move_id, int) or str(move_id).isdigit()
		if not is_id:
			move_id = str(move_id).lower()
		try:
			with open("data/api/moves.json", "r") as f:
				parser = ijson.items(f, "item")
				for move in parser:
					if is_id:
						if move.get("id") == int(move_id):
							result = move
							del move
							gc.collect()
							return munchify(result)
					else:
						if move.get("name") == move_id:
							result = move
							del move
							gc.collect()
							return munchify(result)
		except Exception as e:
			self.logger.error(f"Erro ao ler moves.json: {e}")
			return None
		finally:
			gc.collect()
		return None
	
	async def get_species(self, species_id: int) -> Munch:
		resp = await self._request(f"pokemon-species/{species_id}")
		chain_id = self._extract_id_from_url(resp.evolution_chain.url)
		resp.evolution_chain.id = chain_id
		return resp

	async def get_evolution_chain(self, chain_id: int) -> Munch:
		try:
			with open("data/api/evolution-chain.json", "r") as f:
				parser = ijson.items(f, "item")
				for chain in parser:
					if chain.get("id") == chain_id:
						result = chain
						del chain
						gc.collect()
						return munchify(result)
		except Exception as e:
			self.logger.error(f"Erro ao ler evolution-chain.json: {e}")
			return None
		finally:
			gc.collect()
		return None

	async def get_item(self, identifier: Union[str, int]) -> Munch:
		is_id = isinstance(identifier, int) or str(identifier).isdigit()
		if not is_id:
			identifier = str(identifier).lower()
		try:
			with open("data/api/items.json", "r") as f:
				parser = ijson.items(f, "item")
				for item in parser:
					if is_id:
						if item.get("id") == int(identifier):
							result = item
							del item
							gc.collect()
							return munchify(result)
					else:
						if item.get("name") == identifier:
							result = item
							del item
							gc.collect()
							return munchify(result)
		except Exception as e:
			self.logger.error(f"Erro ao ler items.json: {e}")
			return None
		finally:
			gc.collect()
		return None

	@staticmethod
	def get_base_stats(poke) -> Dict[str, int]:
		return {s.stat.name: s.base_stat for s in poke.stats}

	@staticmethod
	def choose_ability(poke) -> str:
		regular = [a.ability.name for a in poke.abilities if not a.is_hidden]
		if regular:
			return random.choice(regular)
		return poke.abilities[0].ability.name

	@staticmethod
	def get_level_up_moves(poke, max_level: Optional[int] = None, min_level: Optional[int] = None) -> List[Tuple[str, int]]:
		moves_data = {}
		
		for move_entry in poke.moves:
			best_level = None
			
			learn_level = move_entry.level_learned_at or 0
			
			if max_level is not None and learn_level > max_level:
				continue
			
			if min_level is not None and learn_level <= min_level:
				continue

			if move_entry.move_learn_method != "level-up":
				continue
			
			if best_level is None or learn_level > best_level:
				best_level = learn_level
			
			if best_level is not None:
				move_id = move_entry.name
				if move_id not in moves_data:
					moves_data[move_id] = best_level
		
		result = [(move_id, level) for move_id, level in moves_data.items()]
		result.sort(key=lambda x: (x[1], x[0]))
		
		del moves_data
		return result

	async def select_level_up_moves(self, poke, level: int) -> List[Dict]:
		moves = self.get_level_up_moves(poke, max_level=level)
		result = []
		for move_id, _ in moves[-4:]:
			move_data = await self.get_move(move_id)
			pp_max = move_data.pp if move_data else 35
			result.append({"id": move_id, "pp": pp_max, "pp_max": pp_max})
			del move_data
		del moves
		return result

	def get_future_moves(self, poke, current_level: int) -> List[Tuple[int, str]]:
		moves = self.get_level_up_moves(poke, min_level=current_level)
		result = [(level, move_id) for move_id, level in moves]
		del moves
		return result

	@staticmethod
	def roll_gender(species, forced: Optional[str] = None) -> str:
		if forced in ("Male", "Female", "Genderless"):
			return forced
		gr = getattr(species, "gender_rate", -1)
		if gr == -1:
			return "Genderless"
		female_chance = gr * 12.5
		return "Female" if random.random() * 100 < female_chance else "Male"

	@staticmethod
	def roll_shiny() -> bool:
		return random.randint(1, SHINY_ROLL) == 1











