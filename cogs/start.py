import discord
import random
from __main__ import toolkit, pm
from discord.ext import commands
from pokemon_sdk.constants import NATURES
from pokemon_sdk.calculations import generate_pokemon_data

STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
STARTERS = {"bulbasaur": 1, "charmander": 4, "squirtle": 7, "pikachu": 25}

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

		toolkit.add_user(self.user_id, interaction.user.name, "Male")
		user = toolkit.get_user(self.user_id)
		if not user:
			await interaction.followup.send("Conta não encontrada.", ephemeral=True)
			return

		trainer_gender = norm_trainer_gender(user.get("gender"))
		poke = await pm.service.get_pokemon(self.species_id)
		base_stats = pm.service.get_base_stats(poke)

		ivs = {k: random.randint(0, 31) for k in base_stats.keys()}
		nature = random.choice(list(NATURES.keys()))
		gen = generate_pokemon_data(base_stats, level=5, nature=nature, ivs=ivs)
		ability = pm.service.choose_ability(poke)
		moves = pm.service.select_level_up_moves(poke, 5)

		created = await pm.create_pokemon(
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
				f"Você escolheu **{poke.name.capitalize()}** como seu inicial!\n"
				f"Natureza: **{nature}**\n"
				f"Gênero: **{trainer_gender}**\n"
				f"HP: **{gen['current_hp']} / {gen['stats']['hp']}**"
			),
			view=None
		)

class Start(commands.Cog):
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



