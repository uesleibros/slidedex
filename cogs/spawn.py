import random
import discord
from discord.ext import commands
from __main__ import pm, battle_tracker
from utils.preloaded import preloaded_backgrounds
from utils.spawn_text import get_spawn_text
from utils.canvas import compose_pokemon_async
from utils.formatting import format_pokemon_display
from pokemon_sdk.battle.wild import WildBattle
from pokemon_sdk.constants import SHINY_ROLL

class BattleView(discord.ui.View):
	def __init__(self, author: discord.Member, wild_data: dict, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.author = author
		self.wild_data = wild_data

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⚔️")
	async def battle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.author.id:
			return await interaction.response.send_message(
				"Você não pode iniciar essa batalha!",
				ephemeral=True
			)

		if battle_tracker.is_battling(str(self.author.id)):
			return await interaction.response.send_message(
				"Você não pode ir para uma batalha enquanto já está em outra.", 
				ephemeral=True
			)
		try:
			player_party = pm.repo.tk.get_user_party(str(self.author.id))
		except ValueError:
			player_party = None
			
		if not player_party:
			return
		
		await interaction.response.defer()
		
		battle = WildBattle(player_party, self.wild_data, str(self.author.id), interaction)
		
		if not await battle.setup():
			return
		
		for item in self.children:
			item.disabled = True
		
		await interaction.message.edit(view=self)
		self.stop()
		
		await battle.start()

class Spawn(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.preloaded_backgrounds = preloaded_backgrounds

	@commands.command(name="spawn", aliases=["sp"])
	async def spawn_command(self, ctx: commands.Context) -> None:
		is_shiny = False
		
		if random.randint(1, SHINY_ROLL) == 1:
			is_shiny = True
			
		pokemon_query = str(random.randint(1, 386))
		
		poke = await pm.service.get_pokemon(pokemon_query.lower())
		species = await pm.service.get_species(poke.id)

		is_legendary = bool(getattr(species, "is_legendary", False))
		is_mythical = bool(getattr(species, "is_mythical", False))
		habitat_name = (
			species.habitat.name if species.habitat 
			else ("rare" if (is_legendary or is_mythical) else "grassland")
		)

		sprite = poke.sprites.front_shiny if is_shiny and poke.sprites.front_shiny else poke.sprites.front_default
		sprite_bytes = await sprite.read() if sprite else None

		try:
			player_party = pm.repo.tk.get_user_party(str(ctx.author.id))
		except ValueError:
			player_party = None
			
		if player_party:
			active_level = player_party[0]["level"]
			min_level = max(2, active_level - 5)
			max_level = min(100, active_level + 5)
			level = random.randint(min_level, max_level)
		else:
			level = random.randint(5, 15)

		wild = await pm.generate_temp_pokemon(
			owner_id="wild",
			species_id=poke.id,
			level=level,
			on_party=False,
			shiny=is_shiny
		)

		buffer = await compose_pokemon_async(sprite_bytes, self.preloaded_backgrounds[habitat_name])
		file = discord.File(fp=buffer, filename="spawn.png")

		title = "✨ Um Pokémon Shiny Selvagem Apareceu! ✨" if is_shiny else "Um Pokémon Selvagem Apareceu!"
		desc = get_spawn_text(habitat_name, f"{format_pokemon_display(wild, bold_name=True)}!")

		embed = discord.Embed(
			title=title,
			description=desc,
			color=discord.Color.gold() if is_shiny else discord.Color.green()
		)
		embed.set_image(url="attachment://spawn.png")

		del poke
		del species
		await ctx.send(embed=embed, file=file, view=BattleView(ctx.author, wild))

async def setup(bot: commands.Bot):
	await bot.add_cog(Spawn(bot))











