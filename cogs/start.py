import discord
from __main__ import toolkit, pm
from discord.ext import commands
from pokemon_sdk.constants import NATURES, STAT_KEYS
from pokemon_sdk.calculations import generate_pokemon_data, calculate_stats
from utils.formatting import format_pokemon_display

STARTERS = {"bulbasaur": 1, "charmander": 4, "squirtle": 7, "pikachu": 25, "eevee": 133}

def norm_trainer_gender(g: str) -> str:
	s = (g or "").strip().lower()
	if s in ("male", "m", "masc", "homem"):
		return "Male"
	if s in ("female", "f", "fem", "mulher"):
		return "Female"
	return "Genderless"

class StarterChoice(discord.ui.View):
	def __init__(self, user_id: str):
		super().__init__(timeout=30)
		self.user_id = user_id
		for name, sid in STARTERS.items():
			self.add_item(StarterButton(name, sid, user_id))

class StarterButton(discord.ui.Button):
	def __init__(self, name, species_id, user_id):
		super().__init__(label=name.capitalize(), style=discord.ButtonStyle.primary)
		self.species_id = species_id
		self.user_id = user_id

	async def callback(self, interaction: discord.Interaction):
		if str(interaction.user.id) != self.user_id:
			await interaction.response.send_message("Não é você quem deve escolher esse inicial.", ephemeral=True)
			return

		await interaction.response.defer()

		user = toolkit.get_user(self.user_id)
		if user:
			await interaction.followup.send("Você já escolheu seu inicial! Não dá para escolher outro.", ephemeral=True)
			return

		toolkit.add_user(self.user_id, "Male")
		user = toolkit.get_user(self.user_id)
		trainer_gender = norm_trainer_gender(user.get("gender"))
		poke = pm.service.get_pokemon(self.species_id)
		base_stats = pm.service.get_base_stats(poke)

		ivs = toolkit.roll_ivs(self.user_id)
		evs = {k: 0 for k in base_stats.keys()}
		nature = toolkit.roll_nature(self.user_id)
		
		calculated_stats = calculate_stats(base_stats, ivs, evs, 5, nature)
		
		ability = pm.tk.roll_ability(poke, self.user_id)
		moves = pm.service.select_level_up_moves(poke, 5)

		pm.create_pokemon(
			owner_id=self.user_id,
			species_id=self.species_id,
			level=5,
			forced_gender=trainer_gender,
			on_party=True,
			ivs=ivs,
			nature=nature,
			ability=ability,
			moves=moves,
			shiny=False
		)

		await interaction.followup.edit_message(
			message_id=interaction.message.id,
			content=(
				f"Você escolheu **{format_pokemon_display(poke)}** como seu inicial!\n"
				f"Natureza: **{nature}**\n"
				f"Habilidade: **{ability}**\n"
				f"HP: **{calculated_stats['hp']} / {calculated_stats['hp']}**\n"
				"-# Use !help para ver os comandos disponíveis • Boa sorte na sua jornada!"
			),
			view=None
		)

class Start(commands.Cog):
	""" Comece sua jornada. """
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name="start")
	async def start_command(self, ctx: commands.Context):
		user_id = str(ctx.author.id)

		existing = toolkit.get_user(user_id)
		if existing:
			await ctx.send("Você já começou sua jornada!")
			return

		view = StarterChoice(user_id)
		await ctx.send(f"{ctx.author.mention}, escolha seu inicial:", view=view)

async def setup(bot: commands.Bot):
	await bot.add_cog(Start(bot))


