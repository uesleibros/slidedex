import discord
import aiopoke
import random
from __main__ import pm
from typing import List, Dict, Any
from utils.canvas import compose_battle_async
from pokemon_sdk.calculations import calculate_stats
from utils.preloaded import preloaded_textures
from utils.pokemon_emojis import get_app_emoji

class WildBattleView(discord.ui.View):
	def __init__(self, user_id: str, wild_data: dict, active_poke: dict, timeout=60.0) -> None:
		super().__init__(timeout=timeout)
		self.user_id = user_id
		self.active_poke = active_poke
		self.wild_data = wild_data
		
	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>")
	async def capture_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != str(self.user_id):
			return await interaction.response.send_message("Esse Pokémon não é seu para capturar!", ephemeral=True)

		level = self.wild_data.get("level", 10)
		base_chance = max(5, 50 - (level // 2))
		if self.wild_data.get("is_shiny"):
			base_chance += 10

		roll = random.randint(1, 100)
		poke_emoji = get_app_emoji(f"p_{self.wild_data['species_id']}")
		
		if roll <= base_chance:
			xp_gain = pm.repo.tk.calc_battle_exp(self.active_poke["level"], self.wild_data["level"])
			pm.repo.tk.add_exp(user_id, self.active_poke["id"], xp_gain)
			pm.repo.tk.add_pokemon(
				owner_id=self.user_id,
				species_id=self.wild_data["species_id"],
				ivs=self.wild_data["ivs"],
				nature=self.wild_data["nature"],
				ability=self.wild_data["ability"],
				gender=self.wild_data["gender"],
				shiny=self.wild_data.get("is_shiny", False),
				level=self.wild_data["level"],
				exp=self.wild_data.get("exp", 0),
				moves=self.wild_data.get("moves", []),
				nickname=self.wild_data.get("nickname"),
				name=self.wild_data.get("name"),
				current_hp=self.wild_data.get("current_hp"),
				on_party=pm.repo.tk.can_add_to_party(self.user_id)
			)
			await interaction.response.send_message(f"{interaction.user.mention} capturou {poke_emoji} **{self.wild_data['name'].capitalize()}** (Lv {level}) com sucesso!\nAproveitando seu Pokémon recebeu **{xp_gain}** de XP.")
		else:
			await interaction.response.send_message(f"💨 O {poke_emoji} **{self.wild_data['name'].capitalize()}** escapou!")
		
		for item in self.children:
			item.disabled = True

		await interaction.message.edit(view=self)
		self.stop()

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

		await self.interaction.channel.send(embed=embed, file=file, view=WildBattleView(self.user_id, self.wild_raw, self.player_party[self.active_player_idx]))

