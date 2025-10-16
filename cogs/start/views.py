import discord
import asyncio
from sdk.toolkit import Toolkit
from sdk.calculations import PokemonDataGenerator
from sdk.factories.pokemon_factory import PokemonFactory
from utilities.formatting import format_pokemon_display
from typing import Final

STARTERS: Final[dict[str, int]] = {
	"bulbasaur": 1,
	"charmander": 4,
	"squirtle": 7,
	"pikachu": 25,
	"eevee": 133
}

STARTER_LEVEL: Final[int] = 5
STARTER_TIMEOUT: Final[int] = 60

class Gender:
	MALE = "Male"
	FEMALE = "Female"
	GENDERLESS = "Genderless"
	
	@classmethod
	def normalize(cls, gender: str) -> str:
		gender = (gender or "").strip().lower()
		if gender == "male":
			return cls.MALE
		if gender == "female":
			return cls.FEMALE
		return cls.GENDERLESS

class StarterService:
	def __init__(self):
		self.tk: toolkit = Toolkit()

	def create_account(self, user_id: str, gender: str = Gender.MALE) -> dict:
		return self.tk.add_user(user_id, gender)

	def user_has_account(self, user_id: str) -> bool:
		return self.tk.get_user(user_id) is not None

	def create_starter_pokemon(self, user_id: str, species_id: int, trainer_gender: str) -> dict:
		return self.tk.create_pokemon(
			owner_id=user_id,
			species_id=species_id,
			level=STARTER_LEVEL,
			gender=trainer_gender,
			is_shiny=False,
			on_party=True,
			caught_with="poke-ball"
		)

	def get_starter_summary(self, pokemon: dict) -> str:
		summary = PokemonDataGenerator.generate_summary(pokemon)
		
		return (
			f"Você escolheu **{format_pokemon_display(pokemon)}** como seu inicial!\n\n"
			f"**Informações:**\n"
			f"├ Natureza: **{pokemon['nature']}**\n"
			f"├ Habilidade: **{pokemon['ability'].replace('-', ' ').title()}**\n"
			f"├ HP: **{summary['max_hp']}**\n"
			f"└ IVs: **{summary['iv_percent']:.1f}%** ({summary['iv_total']}/186)\n\n"
			f"-# Use .help para ver os comandos disponíveis • Boa sorte na sua jornada!"
		)

class StarterButton(discord.ui.Button):
	def __init__(self, name: str, species_id: int, user_id: str):
		super().__init__(
			label=name.capitalize(),
			style=discord.ButtonStyle.primary,
			custom_id=f"starter_{species_id}"
		)
		self.species_id = species_id
		self.user_id = user_id
		self.service = StarterService()

	async def callback(self, interaction: discord.Interaction) -> None:
		await interaction.response.defer()

		if await asyncio.to_thread(self.service.user_has_account(self.user_id)):
			await interaction.followup.send(
				"Você já tem uma conta! Não pode escolher outro inicial.",
				ephemeral=True
			)
			return

		user = await asyncio.to_thread(self.service.create_account(self.user_id, Gender.MALE))
		trainer_gender = Gender.normalize(user.get("gender", Gender.MALE))

		pokemon = await asyncio.to_thread(self.service.create_starter_pokemon(
			self.user_id,
			self.species_id,
			trainer_gender
		))

		summary = await asyncio.to_thread(self.service.get_starter_summary(pokemon))
		await interaction.followup.edit_message(
			message_id=interaction.message.id,
			content=summary,
			view=None
		)

		self.view.stop()

class StarterView(discord.ui.View):
	def __init__(self, user_id: str):
		super().__init__(timeout=STARTER_TIMEOUT)
		self.user_id = user_id
		self._add_starter_buttons()

	def _add_starter_buttons(self) -> None:
		for name, species_id in STARTERS.items():
			self.add_item(StarterButton(name, species_id, self.user_id))

	async def on_timeout(self) -> None:
		for item in self.children:
			item.disabled = True

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return str(interaction.user.id) == self.user_id
