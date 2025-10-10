import asyncio
import discord
from discord.ext import commands
from __main__ import pm, battle_tracker
from utils.preloaded import preloaded_backgrounds
from utils.spawn_text import get_spawn_text
from utils.canvas import compose_pokemon_async
from utils.formatting import format_pokemon_display
from pokemon_sdk.battle.core.wild import WildBattle
from pokemon_sdk.constants import SHINY_ROLL
from helpers.checks import requires_account

class BattleView(discord.ui.View):
	def __init__(self, wild_data: dict, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.wild_data = wild_data

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⚔️")
	async def battle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		author_id = str(interaction.user.id)
		
		if battle_tracker.is_battling(author_id):
			return await interaction.response.send_message("Você não pode ir para uma batalha enquanto já está em outra.", ephemeral=True)
		
		try:
			player_party = pm.tk.get_user_party(author_id)
		except ValueError:
			return
			
		if not player_party:
			return
		
		await interaction.response.defer()
		
		battle = WildBattle(player_party, self.wild_data, author_id, interaction)
		
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

	def find_min_level_in_chain(self, chain, species_name: str, current_min_level: int = 1):
		if chain.species.name == species_name:
			return current_min_level
		
		for evolution in chain.evolves_to:
			next_min_level = current_min_level
			
			if evolution.evolution_details:
				for detail in evolution.evolution_details:
					if detail.min_level > 0:
						next_min_level = detail.min_level
						break
			
			result = self.find_min_level_in_chain(evolution, species_name, next_min_level)
			if result is not None:
				return result

	def get_pokemon_min_level(self, species) -> int:
		if not species.evolution_chain:
			return 1
		
		try:
			chain_data = pm.service.client.get_evolution_chain(species.evolution_chain.id)
			return self.find_min_level_in_chain(chain_data.chain, species.name) or 1
		except:
			return 1

	@commands.command(name="spawn", aliases=["sp"])
	@requires_account()
	async def spawn_command(self, ctx: commands.Context) -> None:
		author_id = str(ctx.author.id)
		
		is_shiny = pm.tk.roll_shiny(author_id)
		pokemon_id = pm.tk.roll_random(author_id, 1, 387)
		
		species = pm.service.get_species(pokemon_id)

		is_legendary = bool(getattr(species, "is_legendary", False))
		is_mythical = bool(getattr(species, "is_mythical", False))
		habitat_name = species.habitat.name if species.habitat else ("rare" if (is_legendary or is_mythical) else "grassland")

		pokemon_min_level = self.get_pokemon_min_level(species)

		try:
			player_party = pm.tk.get_user_party(author_id)
			active_level = player_party[0]["level"]
			min_level = max(pokemon_min_level, active_level - 5)
			max_level = max(min_level, min(100, active_level + 5))
			level = pm.tk.roll_random(author_id, min_level, max_level + 1)
		except ValueError:
			level = pm.tk.roll_random(author_id, pokemon_min_level, max(pokemon_min_level, 15) + 1)

		wild = pm.generate_temp_pokemon(
			owner_id="wild",
			species_id=pokemon_id,
			level=level,
			on_party=False,
			shiny=is_shiny
		)

		sprite_bytes = pm.service.get_pokemon_sprite({
			"species_id": pokemon_id,
			"is_shiny": is_shiny,
			"gender": "Male"
		})[0]

		buffer = await compose_pokemon_async(sprite_bytes, self.preloaded_backgrounds[habitat_name])
		
		title = "✨ Um Pokémon Shiny Selvagem Apareceu! ✨" if is_shiny else "Um Pokémon Selvagem Apareceu!"
		
		embed = discord.Embed(
			title=title,
			description=get_spawn_text(habitat_name, f"{format_pokemon_display(wild, bold_name=True)}!"),
			color=discord.Color.gold() if is_shiny else discord.Color.green()
		)
		embed.set_image(url="attachment://spawn.png")

		await ctx.send(embed=embed, file=discord.File(fp=buffer, filename="spawn.png"), view=BattleView(wild))

async def setup(bot: commands.Bot):
	await bot.add_cog(Spawn(bot))
