import random
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
	""" [DEV] Comandos de Spawn. """
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

	async def get_pokemon_min_level(self, species) -> int:
		if not species.evolution_chain:
			return 1
		
		try:
			chain_id = int(species.evolution_chain.url.rstrip('/').split('/')[-1])
			chain_data = await pm.service.client.get_evolution_chain(chain_id)
			return self.find_min_level_in_chain(chain_data.chain, species.name) or 1
		except:
			return 1

	@commands.command(name="spawn", aliases=["sp"])
	@requires_account()
	async def spawn_command(self, ctx: commands.Context) -> None:
		is_shiny = random.randint(1, SHINY_ROLL) == 1
		poke = await pm.service.get_pokemon(str(random.randint(1, 386)))
		species = await pm.service.get_species(poke.id)

		is_legendary = bool(getattr(species, "is_legendary", False))
		is_mythical = bool(getattr(species, "is_mythical", False))
		habitat_name = species.habitat.name if species.habitat else ("rare" if (is_legendary or is_mythical) else "grassland")

		sprite = poke.sprites.front_shiny if is_shiny and poke.sprites.front_shiny else poke.sprites.front_default
		sprite_bytes = await pm.service.get_bytes(sprite) if sprite else None
		pokemon_min_level = await self.get_pokemon_min_level(species)

		author_id = str(ctx.author.id)
		try:
			player_party = pm.tk.get_user_party(author_id)
			active_level = player_party[0]["level"]
			min_level = max(pokemon_min_level, active_level - 5)
			max_level = max(min_level, min(100, active_level + 5))
			level = random.randint(min_level, max_level)
		except ValueError:
			level = random.randint(pokemon_min_level, max(pokemon_min_level, 15))

		wild = await pm.generate_temp_pokemon(owner_id="wild", species_id=poke.id, level=level, on_party=False, shiny=is_shiny)
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
