import discord
import asyncio
from sdk.toolkit import Toolkit
from sdk.calculations import PokemonDataGenerator
from sdk.factories.pokemon_factory import PokemonFactory
from utilities.formatting import format_pokemon_display
from typing import Final

STARTERS: Final[tuple[tuple[str, int], ...]] = (
    ("bulbasaur", 1),
    ("charmander", 4),
    ("squirtle", 7),
    ("pikachu", 25),
    ("eevee", 133)
)

STARTER_LEVEL: Final[int] = 5
STARTER_TIMEOUT: Final[int] = 60

class Gender:
    MALE = "Male"
    FEMALE = "Female"
    GENDERLESS = "Genderless"
    
    _GENDER_MAP: Final[dict[str, str]] = {
        "male": MALE,
        "m": MALE,
        "female": FEMALE,
        "f": FEMALE,
    }
    
    @classmethod
    def normalize(cls, gender: str) -> str:
        return cls._GENDER_MAP.get((gender or "").strip().lower(), cls.GENDERLESS)

class StarterService:
    __slots__ = ('tk',)
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tk = Toolkit()
        return cls._instance

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

    @staticmethod
    def get_starter_summary(pokemon: dict) -> str:
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
    __slots__ = ('species_id', 'user_id', '_service')
    
    _shared_service = StarterService()
    
    def __init__(self, name: str, species_id: int, user_id: str):
        super().__init__(
            label=name.capitalize(),
            style=discord.ButtonStyle.primary,
            custom_id=f"starter_{species_id}"
        )
        self.species_id = species_id
        self.user_id = user_id
        self._service = self._shared_service

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        
        svc = self._service
        user_id = self.user_id
        
        if await asyncio.to_thread(svc.user_has_account, user_id):
            await interaction.followup.send(
                "Você já tem uma conta! Não pode escolher outro inicial.",
                ephemeral=True
            )
            return

        user, pokemon = await asyncio.to_thread(
            self._create_account_and_pokemon,
            svc,
            user_id,
            self.species_id
        )

        summary = svc.get_starter_summary(pokemon)
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content=summary,
            view=None
        )

        self.view.stop()
    
    @staticmethod
    def _create_account_and_pokemon(svc: StarterService, user_id: str, species_id: int) -> tuple[dict, dict]:
        user = svc.create_account(user_id, Gender.MALE)
        trainer_gender = Gender.normalize(user.get("gender", Gender.MALE))
        pokemon = svc.create_starter_pokemon(user_id, species_id, trainer_gender)
        return user, pokemon

class StarterView(discord.ui.View):
    __slots__ = ('user_id',)
    
    def __init__(self, user_id: str):
        super().__init__(timeout=STARTER_TIMEOUT)
        self.user_id = user_id
        
        for name, species_id in STARTERS:
            self.add_item(StarterButton(name, species_id, user_id))

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return str(interaction.user.id) == self.user_id
