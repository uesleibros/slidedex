import discord
import aiopoke
from __main__ import pm
from typing import List, Dict, Any
from utils.canvas import compose_battle_async
from pokemon_sdk.calculations import calculate_stats
from utils.preloaded import preloaded_textures
from utils.pokemon_emojis import get_app_emoji

class BattlePokemon:
	def __init__(self, raw: Dict[str, Any], pokeapi_data: aiopoke.Pokemon):
		self.raw = raw
		self.species_id = raw["species_id"]
		self.name = raw.get("name")
		self.nickname = raw.get("nickname")
		self.level = raw["level"]
		base_stats = pm.service.get_base_stats(pokeapi_data)
		self.stats = calculate_stats(
			base_stats,
			raw["ivs"],
			raw["evs"],
			raw["level"],
			raw["nature"]
		)
		self.current_hp = raw.get("current_hp") or self.stats["hp"]
		self.moves = raw.get("moves", [])
		self.pokeapi_data = pokeapi_data
		self.is_shiny = raw.get("is_shiny", False)

		if self.is_shiny:
			self.sprites = {
				"front": pokeapi_data.sprites.front_shiny,
				"back": pokeapi_data.sprites.back_shiny
			}
		else:
			self.sprites = {
				"front": pokeapi_data.sprites.front_default,
				"back": pokeapi_data.sprites.back_default
			}

class WildBattle:
	def __init__(self, player_party: List[Dict[str, Any]], wild: Dict[str, Any], user_id: str, interaction: discord.Interaction) -> None:
		self.user_id = user_id
		self.interaction = interaction
		self.player_party = player_party
		self.active_player_idx = 0
		self.wild_raw = wild
		self.ended = False

		self.player_team: List[BattlePokemon] = []
		self.wild: BattlePokemon | None = None

	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]

	async def setup(self):
		pokeapi_wild: aiopoke.Pokemon = await pm.service.get_pokemon(self.wild_raw["species_id"])
		self.wild = BattlePokemon(self.wild_raw, pokeapi_wild)

		for p in self.player_party:
			api_p = await pm.service.get_pokemon(p["species_id"])
			self.player_team.append(BattlePokemon(p, api_p))

	async def render_embed(self) -> tuple[discord.Embed, discord.File]:
		player_sprite = None
		if self.player_active.sprites["back"]:
			player_sprite = await self.player_active.sprites["back"].read()

		enemy_sprite = None
		if self.wild and self.wild.sprites["front"]:
			enemy_sprite = await self.wild.sprites["front"].read()

		background = preloaded_textures["battle"]
		buf = await compose_battle_async(player_sprite, enemy_sprite, background)

		file = discord.File(buf, filename="battle.png")
		player_emoji = get_app_emoji(f"p_{self.player_active.species_id}")
		enemy_emoji = get_app_emoji(f"p_{self.wild.species_id}")

		embed = discord.Embed(
			title=f"Luta",
			description=(f"Lv{self.player_active.level} {player_emoji} {self.player_active.name.title()} "
						 f"(HP {self.player_active.current_hp}/{self.player_active.stats['hp']})\n"
						 f"VS\n"
						 f"Lv{self.wild.level} {enemy_emoji} {self.wild.name.title()} "
						 f"(HP {self.wild.current_hp}/{self.wild.stats['hp']}) *Wild*"),
			color=discord.Color.green()
		)
		embed.set_image(url="attachment://battle.png")

		return embed, file


