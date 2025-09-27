import io
import random
import discord
from discord.ext import commands
from typing import Optional

from __main__ import pm
from utils.preloaded import preloaded_backgrounds
from utils.pokemon_emojis import get_app_emoji
from utils.spawn_text import get_spawn_text
from utils.canvas import compose_pokemon

class BattleView(discord.ui.View):
	def __init__(self, author: discord.Member, wild_pokemon_name: str, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.author = author
		self.target_name = wild_pokemon_name

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⚔️")
	async def battle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message(
			f"{interaction.user.mention} iniciou uma batalha contra **{self.target_name}**!", 
			ephemeral=False
		)
		for item in self.children:
			item.disabled = True
		await interaction.message.edit(view=self)
		self.stop()

class Spawn(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.preloaded_backgrounds = preloaded_backgrounds

	@commands.command(name="spawn", aliases=["sp"])
	async def spawn_command(self, ctx: commands.Context, pokemon_query: Optional[str] = None) -> None:
		is_shiny = False
		if not pokemon_query:
			pokemon_query = str(random.randint(1, 386))
		if "=shiny" in pokemon_query.lower():
			is_shiny = True
			pokemon_query = pokemon_query.replace("=shiny", "").strip()

		poke = await pm.service.get_pokemon(pokemon_query.lower())
		species = await pm.service.get_species(poke.id)

		name = poke.name.capitalize()
		emoji = get_app_emoji(f"p_{poke.id}")

		is_legendary = bool(getattr(species, "is_legendary", False))
		is_mythical = bool(getattr(species, "is_mythical", False))
		habitat_name = (
			species.habitat.name if species.habitat 
			else ("rare" if (is_legendary or is_mythical) else "grassland")
		)

		sprite = poke.sprites.front_shiny if is_shiny and poke.sprites.front_shiny else poke.sprites.front_default
		sprite_bytes = await sprite.read() if sprite else None

		level = random.randint(5, 45)

		wild = await pm.generate_temp_pokemon(
			owner_id="wild",
			species_id=poke.id,
			level=level,
			on_party=False,
			shiny=is_shiny
		)

		buffer = compose_pokemon(sprite_bytes, self.preloaded_backgrounds[habitat_name])
		file = discord.File(fp=buffer, filename="spawn.png")

		title = "✨ Um Pokémon Shiny Selvagem Apareceu! ✨" if is_shiny else "Um Pokémon Selvagem Apareceu!"
		desc = get_spawn_text(habitat_name, f"{emoji} **{name}**{' SHINY' if is_shiny else ''}!")

		embed = discord.Embed(
			title=title,
			description=desc,
			color=discord.Color.gold() if is_shiny else discord.Color.green()
		)
		embed.set_image(url="attachment://spawn.png")

		await ctx.send(embed=embed, file=file, view=BattleView(ctx.author, name))

async def setup(bot: commands.Bot):
	await bot.add_cog(Spawn(bot))


