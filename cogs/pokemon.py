import random
from typing import Dict, List, Literal, Optional
import discord
from discord.ext import commands
from utils.pokemon_emojis import get_app_emoji
from pokemon_sdk.calculations import iv_percent
from utils.formatting import format_poke_id
from __main__ import toolkit

class PokemonFlags(commands.FlagConverter, delimiter=" ", prefix="--"):
	party: Optional[bool] = commands.flag(default=False, max_args=0)
	box: Optional[bool] = commands.flag(default=False, max_args=0)
	shiny: Optional[bool] = commands.flag(default=False, max_args=0)
	favorite: Optional[bool] = commands.flag(default=False, max_args=0)
	reverse: Optional[bool] = commands.flag(default=False, max_args=0)
	random: Optional[bool] = commands.flag(default=False, max_args=0)

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
	sort: Optional[Literal["iv", "level", "id", "name", "species"]] = None
	limit: Optional[int] = None
	page_size: Optional[int] = None

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
			nickname = f" ({p['nickname']})" if p.get("nickname") else ""
			if p["gender"] != "Genderless":
				gender = ":male_sign:" if p["gender"] == "Male" else ":female_sign:"
			else:
				gender = ":grey_question:"
			ivp = iv_percent(p["ivs"])
			desc_lines.append(
				f"`{format_poke_id(poke_id)}`　{emoji}{shiny} {p['name'].title()}{nickname} {gender}　•　Lv. {p['level']}　•　{ivp}%"
			)
		embed = discord.Embed(
			title="Seus Pokémon",
			description="\n".join(desc_lines) if desc_lines else "Sem resultados",
			color=discord.Color.pink()
		)
		embed.set_footer(text=f"Mostrando {start+1}–{end} de {self.total}")
		return embed

	@discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
	async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = 0
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
	async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_page > 0:
			self.current_page -= 1
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
	async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		max_page = (self.total - 1) // self.page_size
		if self.current_page < max_page:
			self.current_page += 1
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
	async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = (self.total - 1) // self.page_size
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)


def apply_filters(pokemons: List[Dict], flags: PokemonFlags) -> List[Dict]:
	res = pokemons
	if flags.box and not flags.party:
		res = [p for p in res if not p.get("on_party", False)]
	if flags.party and not flags.box:
		res = [p for p in res if p.get("on_party", False)]
	if flags.shiny:
		res = [p for p in res if p.get("is_shiny", False)]
	if flags.favorite:
		res = [p for p in res if p.get("is_favorite")]
	if flags.gender:
		res = [p for p in res if p["gender"].lower() == flags.gender]
	if flags.min_iv is not None:
		res = [p for p in res if iv_percent(p["ivs"]) >= flags.min_iv]
	if flags.max_iv is not None:
		res = [p for p in res if iv_percent(p["ivs"]) <= flags.max_iv]
	if flags.min_level is not None:
		res = [p for p in res if p["level"] >= flags.min_level]
	if flags.max_level is not None:
		res = [p for p in res if p["level"] <= flags.max_level]
	if flags.species is not None:
		res = [p for p in res if p["species_id"] == flags.species]
	if flags.name:
		q = flags.name.lower()
		res = [p for p in res if q in (p.get("nickname") or p.get("name", "")).lower()]
	if flags.nature:
		res = [p for p in res if p["nature"].lower() == flags.nature.lower()]
	if flags.ability:
		res = [p for p in res if p["ability"].lower() == flags.ability.lower()]
	if flags.held_item:
		res = [p for p in res if p.get("held_item") and p["held_item"].lower() == flags.held_item.lower()]
	return res


def apply_sort_limit(pokemons: List[Dict], flags: PokemonFlags) -> List[Dict]:
	res = list(pokemons)
	if flags.random:
		random.shuffle(res)
	elif flags.sort:
		keymap = {
			"iv": lambda p: iv_percent(p["ivs"]),
			"level": lambda p: p["level"],
			"id": lambda p: p["id"],
			"name": lambda p: (p.get("nickname") or p.get("name", "")).lower(),
			"species": lambda p: p["species_id"],
		}
		res.sort(key=keymap[flags.sort], reverse=bool(flags.reverse))
	if flags.limit is not None and flags.limit > 0:
		res = res[:flags.limit]
	return res


class Pokemon(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.cooldown(3, 5, commands.BucketType.user)
	@commands.command(
		name="pokemon",
		aliases=["p", "pk", "pkm", "pkmn"],
		help=(
			"Lista seus Pokémon com filtros e ordenação.\n\n"
			"Flags (todos opcionais):\n"
			"  --party       Apenas os que estão na party\n"
			"  --box         Apenas os que estão na box\n"
			"  --shiny       Apenas shinies\n"
			"  --favorite    Apenas favoritos\n"
			"  --random      Embaralha a ordem da listagem\n"
			"  --reverse     Inverte a ordem do sort\n\n"
			"Filtros avançados:\n"
			"  --gender male|female|genderless\n"
			"  --min_iv N    IV mínimo\n"
			"  --max_iv N    IV máximo\n"
			"  --min_level N Nível mínimo\n"
			"  --max_level N Nível máximo\n"
			"  --species ID  Species específico (numérico)\n"
			"  --name TEXTO  Nome ou nickname contendo TEXTO\n"
			"  --nature TEXTO  Nature específica\n"
			"  --ability TEXTO Ability específica\n"
			"  --held_item TEXTO Item segurado\n"
			"  --sort iv|level|id|name|species\n"
			"  --limit N     Limita resultados\n"
			"  --page_size N Quantidade por página na paginação\n\n"
			"Exemplos:\n"
			"  .pokemon --party true\n"
			"  .pokemon --box true --shiny true\n"
			"  .pokemon --min_iv 85 --sort level --reverse true\n"
			"  .pokemon --random true --limit 5"
		)
	)
	async def pokemon_command(self, ctx: commands.Context, *, flags: PokemonFlags):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return

		pokemons = toolkit.get_user_pokemon(user_id)
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		page_size = flags.page_size if flags.page_size and flags.page_size > 0 else 20
		view = Paginator(pokemons, user_id=ctx.author.id, page_size=page_size)
		embed = await view.get_embed()
		await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))