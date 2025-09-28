import random
from typing import Dict, List, Literal, Optional
from discord.ext import commands
from utils.pokemon_emojis import get_app_emoji
from pokemon_sdk.calculations import iv_percent
from __main__ import toolkit, pm
from utils.formatting import format_poke_id
import discord

class PokemonFlags(commands.FlagConverter, delimiter=" ", prefix="--"):
	box: bool = False
	party: bool = False
	shiny: bool = False
	gender: Optional[Literal["male", "female", "genderless"]] = None
	min_iv: Optional[float] = None
	max_iv: Optional[float] = None
	min_level: Optional[int] = None
	max_level: Optional[int] = None
	species: Optional[int] = None
	name: Optional[str] = None
	nature: Optional[str] = None
	ability: Optional[str] = None
	held_item: Optional[str] = None
	favorite: bool = False
	sort: Optional[Literal["iv", "level", "id", "name", "species"]] = None
	reverse: bool = False
	limit: Optional[int] = None
	random: bool = False

class Paginator(discord.ui.View):
	def __init__(self, pokemons, user_id: int, page_size=20):
		super().__init__(timeout=120)
		self.pokemons = pokemons
		self.page_size = page_size
		self.current_page = 0
		self.user_id = user_id
		self.total = len(pokemons)
		self.update_buttons()

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return interaction.user.id == self.user_id

	def update_buttons(self):
		self.first_page.disabled = self.current_page == 0
		self.prev_page.disabled = self.current_page == 0
		max_page = (self.total - 1) // self.page_size
		self.next_page.disabled = self.current_page == max_page
		self.last_page.disabled = self.current_page == max_page

	async def get_embed(self) -> discord.Embed:
		start = self.current_page * self.page_size
		end = min(start + self.page_size, self.total)
		desc_lines = []
		for p in self.pokemons[start:end]:
			poke_id = p["id"]
			emoji = get_app_emoji(f"p_{p['species_id']}")
			shiny = "✨ " if p.get("is_shiny", False) else ""
			nickname = f" ({p['nickname']})" if p.get("nickname") else ''
			if p["gender"] != "Genderless":
				gender = ":male_sign:" if p["gender"] == "Male" else ":female_sign:"
			else:
				gender = ":grey_question:"
			iv_percent_ = iv_percent(p["ivs"])
			desc_lines.append(
				f"`{format_poke_id(poke_id)}`　{emoji}{shiny} {p['name'].title()} {nickname} {gender}　•　Lv. {p['level']}　•　{iv_percent_}%"
			)
		embed = discord.Embed(
			title="Seus Pokémon",
			description="\n".join(desc_lines),
			color=discord.Color.pink()
		)
		embed.set_footer(text=f"Mostrando resultados {start+1}–{end} de {self.total}")
		return embed

	@discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
	async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = 0
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
	async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_page > 0:
			self.current_page -= 1
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
	async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		max_page = (self.total - 1) // self.page_size
		if self.current_page < max_page:
			self.current_page += 1
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
	async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = (self.total - 1) // self.page_size
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)


class Pokemon(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.cooldown(3, 5, commands.BucketType.user)
	@commands.command(name="pokemon", aliases=["p", "pk", "pkm", "pkmn"])
	async def pokemon_command(self, ctx: commands.Context, *, flags: PokemonFlags):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return

		pokemons = toolkit.get_user_pokemon(user_id)

		if flags.box:
			pokemons = [p for p in pokemons if not p.get("on_party", False)]
		if flags.party:
			pokemons = [p for p in pokemons if p.get("on_party", False)]
		if flags.shiny:
			pokemons = [p for p in pokemons if p.get("is_shiny", False)]
		if flags.gender:
			pokemons = [p for p in pokemons if p["gender"].lower() == flags.gender]
		if flags.min_iv:
			pokemons = [p for p in pokemons if iv_percent(p["ivs"]) >= flags.min_iv]
		if flags.max_iv:
			pokemons = [p for p in pokemons if iv_percent(p["ivs"]) <= flags.max_iv]
		if flags.min_level:
			pokemons = [p for p in pokemons if p["level"] >= flags.min_level]
		if flags.max_level:
			pokemons = [p for p in pokemons if p["level"] <= flags.max_level]
		if flags.species:
			pokemons = [p for p in pokemons if p["species_id"] == flags.species]
		if flags.name:
			pokemons = [p for p in pokemons if flags.name.lower() in (p.get("nickname") or p.get("name", "")).lower()]
		if flags.nature:
			pokemons = [p for p in pokemons if p["nature"].lower() == flags.nature.lower()]
		if flags.ability:
			pokemons = [p for p in pokemons if p["ability"].lower() == flags.ability.lower()]
		if flags.held_item:
			pokemons = [p for p in pokemons if p.get("held_item") and p["held_item"].lower() == flags.held_item.lower()]
		if flags.favorite:
			pokemons = [p for p in pokemons if p.get("is_favorite")]

		if flags.sort:
			keymap = {
				"iv": lambda p: iv_percent(p["ivs"]),
				"level": lambda p: p["level"],
				"id": lambda p: p["id"],
				"name": lambda p: (p.get("nickname") or p.get("name", "")).lower(),
				"species": lambda p: p["species_id"]
			}
			pokemons.sort(key=keymap[flags.sort], reverse=flags.reverse)

		if flags.random:
			random.shuffle(pokemons)

		if flags.limit:
			pokemons = pokemons[:flags.limit]

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		view = Paginator(pokemons, user_id=ctx.author.id)
		embed = await view.get_embed()
		await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))

