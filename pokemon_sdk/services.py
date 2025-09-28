import random
from typing import Dict, List, Any, Optional
from aiopoke import AiopokeClient
from .constants import VERSION_GROUPS, SHINY_ROLL
from curl_cffi import AsyncSession, Response

class AiohttpLikeResponse(Response):
    def __init__(self, coro_or_resp):
        self._coro = coro_or_resp
        self._resp: Optional[Response] = None

    def __await__(self):
        async def _():
            if isinstance(self._coro, Response):
                return self._coro
            self._resp = await self._coro
            return self._resp
        return _().__await__()

    async def __aenter__(self):
        self._resp = await self
        return self._resp

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def read(self) -> bytes:
        resp = await self
        return resp.content

class AiohttpLikeSession(AsyncSession):
    def get(self, *args, **kwargs) -> AiohttpLikeResponse:
        return AiohttpLikeResponse(super().get(*args, **kwargs))

    def post(self, *args, **kwargs) -> AiohttpLikeResponse:
        return AiohttpLikeResponse(super().post(*args, **kwargs))

    def put(self, *args, **kwargs) -> AiohttpLikeResponse:
        return AiohttpLikeResponse(super().put(*args, **kwargs))

    def delete(self, *args, **kwargs) -> AiohttpLikeResponse:
        return AiohttpLikeResponse(super().delete(*args, **kwargs))

    def patch(self, *args, **kwargs) -> AiohttpLikeResponse:
        return AiohttpLikeResponse(super().patch(*args, **kwargs))

class HttpClient:
    _session: AiohttpLikeSession
    inexistent_endpoints: List[str]
    base_url: str

    def __init__(self, *, session: Optional[AiohttpLikeSession] = None, base_url: str = "") -> None:
        self._session = session or AiohttpLikeSession()
        self.inexistent_endpoints = []
        self.base_url = base_url.rstrip("/")

    async def close(self) -> None:
        if self._session is not None:
            await self._session.aclose()

    async def get(self, endpoint: str) -> Dict[str, Any]:
        if endpoint in self.inexistent_endpoints:
            raise ValueError(f"The id or name for {endpoint} was not found.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with self._session.get(url) as response:
            if response.status_code == 404:
                self.inexistent_endpoints.append(endpoint)
                raise ValueError(f"The id or name for {endpoint} was not found.")
            return response.json()

class NoCache:
    def get(self, *_, **__): return None
    def put(self, *_, **__): return None
    def has(self, obj: Any): return False

class PokeAPIService:
	def __init__(self):
		self.client = AiopokeClient()
		self.client._cache = NoCache()
		self.client.http = HttpClient(base_url="https://pokeapi.co/api/v2")

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












