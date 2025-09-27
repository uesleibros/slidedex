from discord.ext import commands
from utils.pokemon_emojis import get_app_emoji
from pokemon_sdk.calculations import iv_percent
from __main__ import toolkit, pm
from utils.formatting import format_poke_id
import discord

class Paginator(discord.ui.View):
	def __init__(self, embeds, user_id: int):
		super().__init__(timeout=120)
		self.embeds = embeds
		self.current_page = 0
		self.user_id = user_id
		self.update_buttons()

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return interaction.user.id == self.user_id

	def update_buttons(self):
		self.first_page.disabled = self.current_page == 0
		self.prev_page.disabled = self.current_page == 0
		self.next_page.disabled = self.current_page == len(self.embeds) - 1
		self.last_page.disabled = self.current_page == len(self.embeds) - 1

	@discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
	async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = 0
		self.update_buttons()
		await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

	@discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
	async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_page > 0:
			self.current_page -= 1
		self.update_buttons()
		await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

	@discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
	async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_page < len(self.embeds) - 1:
			self.current_page += 1
		self.update_buttons()
		await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

	@discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
	async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = len(self.embeds) - 1
		self.update_buttons()
		await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

class Pokemon(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name="pokemon", aliases=["p", "pk", "pkm"])
	async def pokemon_command(self, ctx: commands.Context) -> None:
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return

		pokemons = toolkit.get_user_pokemon(user_id)
		if not pokemons:
			await ctx.send("Você não possui nenhum Pokémon ainda!")
			return

		desc_lines = []
		for p in pokemons:
			poke_id = p["id"]
			poke = await pm.services.client.get_pokemon(p["species_id"])
			emoji = get_app_emoji(f"p_{p['species_id']}")
			shiny = "✨ " if p.get("is_shiny", False) else ""
			nickname = f" ({p['nickname']})" if p.get("nickname") else poke.name.title()
			status = ":dagger:" if p.get("on_party", False) else ''
			gender = ":male_sign:" if p["gender"] == "Male" else ":female_sign:"
			level = p["level"]
			ivs = p["ivs"]
			iv_percent_ = iv_percent(ivs)
			desc_lines.append(
				f"`{format_poke_id(poke_id)}`　{emoji}{shiny} **{nickname}** {gender} {status}　•　Lv. {level}　•　{iv_percent_}%"
			)

		chunk_size = 20
		total = len(desc_lines)
		embeds = []
		for i in range(0, total, chunk_size):
			page_lines = desc_lines[i:i+chunk_size]
			embed = discord.Embed(
				title="Seus Pokémon",
				description="\n".join(page_lines),
				color=discord.Color.pink()
			)
			start = i + 1
			end = i + len(page_lines)
			embed.set_footer(text=f"Mostrando resultados {start}–{end} de {total}")
			embeds.append(embed)

		view = Paginator(embeds, user_id=ctx.author.id)
		await ctx.send(embed=embeds[0], view=view)


async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))

