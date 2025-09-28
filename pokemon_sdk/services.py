import random
from typing import Dict, List, Any
from aiopoke import AiopokeClient
from .constants import VERSION_GROUPS, SHINY_ROLL

class NoCache:
    def get(self, *_, **__): return None
    def set(self, *_, **__): return None
    def has(self, obj: Any): return False

class PokeAPIService:
	def __init__(self):
		self.client = AiopokeClient()
		self.client._cache = NoCache()

	async def get_pokemon(self, species_id: int):
		return await self.client.get_pokemon(species_id)

	async def get_species(self, species_id: int):
		return await self.client.get_pokemon_species(species_id)

	def get_base_stats(self, poke) -> Dict[str, int]:
		return {s.stat.name: s.base_stat for s in poke.stats}

	def choose_ability(self, poke) -> str:
		regular = [a.ability.name for a in poke.abilities if not a.is_hidden]
		if regular:
			return random.choice(regular)
		return poke.abilities[0].ability.name

	def select_level_up_moves(self, poke, level: int) -> List[Dict]:
		candidates = {}
		for m in poke.moves:
			best = -1
			for v in m.version_group_details:
				if v.version_group.name not in VERSION_GROUPS:
					continue
				if v.move_learn_method.name != "level-up":
					continue
				if v.level_learned_at <= level and v.level_learned_at > best:
					best = v.level_learned_at
			if best >= 0:
				name = m.move.name
				if name not in candidates or best > candidates[name]:
					candidates[name] = best
		sorted_moves = sorted(candidates.items(), key=lambda x: (x[1], x[0]))
		return [{"id": mv, "pp": 35, "pp_max": 35} for mv, _ in sorted_moves[-4:]]

	def roll_gender(self, species, forced: str = None) -> str:
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


