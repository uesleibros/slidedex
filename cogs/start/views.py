import discord
import asyncio
import pytz
from typing import Final, Optional
from datetime import datetime

class Gender:
    MALE = "Male"
    FEMALE = "Female"
    
    LABELS: Final[dict[str, str]] = {
        MALE: "Masculino",
        FEMALE: "Feminino"
    }
    
    _GENDER_MAP: Final[dict[str, str]] = {
        "male": MALE,
        "m": MALE,
        "masculino": MALE,
        "female": FEMALE,
        "f": FEMALE,
        "feminino": FEMALE,
    }
    
    @classmethod
    def normalize(cls, gender: str) -> str:
        return cls._GENDER_MAP.get((gender or "").strip().lower(), cls.MALE)
    
    @classmethod
    def get_label(cls, value: str) -> str:
        return cls.LABELS.get(value, value)
    
class TimezoneHelper:
    COMMON_BR_TIMEZONES: Final[tuple[tuple[str, str], ...]] = (
        ("America/Sao_Paulo", "🇧🇷 Brasília (UTC-3)"),
        ("America/Manaus", "🇧🇷 Manaus (UTC-4)"),
        ("America/Fortaleza", "🇧🇷 Fortaleza (UTC-3)"),
        ("America/Recife", "🇧🇷 Recife (UTC-3)"),
        ("America/Belem", "🇧🇷 Belém (UTC-3)"),
        ("America/Cuiaba", "🇧🇷 Cuiabá (UTC-4)"),
        ("America/Porto_Velho", "🇧🇷 Porto Velho (UTC-4)"),
        ("America/Boa_Vista", "🇧🇷 Boa Vista (UTC-4)"),
        ("America/Rio_Branco", "🇧🇷 Rio Branco (UTC-5)"),
        ("America/Noronha", "🇧🇷 Fernando de Noronha (UTC-2)"),
    )
    
    OTHER_TIMEZONES: Final[tuple[tuple[str, str], ...]] = (
        ("America/New_York", "🇺🇸 Nova York (UTC-5)"),
        ("America/Los_Angeles", "🇺🇸 Los Angeles (UTC-8)"),
        ("America/Chicago", "🇺🇸 Chicago (UTC-6)"),
        ("Europe/Lisbon", "🇵🇹 Lisboa (UTC+0)"),
        ("Europe/London", "🇬🇧 Londres (UTC+0)"),
        ("Europe/Paris", "🇫🇷 Paris (UTC+1)"),
        ("Europe/Berlin", "🇩🇪 Berlim (UTC+1)"),
        ("Asia/Tokyo", "🇯🇵 Tóquio (UTC+9)"),
        ("Australia/Sydney", "🇦🇺 Sydney (UTC+10)"),
    )
    
    @classmethod
    def get_current_time(cls, tz: str) -> str:
        try:
            timezone = pytz.timezone(tz)
            now = datetime.now(timezone)
            return now.strftime("%H:%M")
        except:
            return "00:00"

class GenderSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=label,
                value=value
            )
            for value, label in Gender.LABELS.items()
        ]
        
        super().__init__(
            placeholder="Selecione o gênero do seu treinador...",
            options=options,
            custom_id="gender_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_gender = self.values[0]
        
        for item in self.view.children:
            if isinstance(item, GenderSelect):
                item.disabled = True
            elif isinstance(item, TimezoneTypeSelect):
                item.disabled = False
        
        await interaction.response.edit_message(
            content=f"✅ Gênero selecionado: **{Gender.get_label(self.values[0])}**\n\n"
                    f"Agora escolha a região do fuso horário:",
            view=self.view
        )

class TimezoneSelect(discord.ui.Select):
    def __init__(self, timezone_type: str = "br"):
        timezones = TimezoneHelper.COMMON_BR_TIMEZONES if timezone_type == "br" else TimezoneHelper.OTHER_TIMEZONES
        
        options = [
            discord.SelectOption(
                label=label,
                value=tz,
                description=f"Agora: {TimezoneHelper.get_current_time(tz)}"
            )
            for tz, label in timezones[:25]
        ]
        
        super().__init__(
            placeholder="Selecione seu fuso horário...",
            options=options,
            custom_id="timezone_select",
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        selected_timezone = self.values[0]
        selected_gender = self.view.selected_gender

        from sdk.database import Database
        from sdk.repositories.user_repository import UserRepository

        db = Database()
        user_repo = UserRepository(db)

        await asyncio.to_thread(
            user_repo.create,
            user_id=user_id,
            gender=selected_gender,
            timezone=selected_timezone
        )

        embed = discord.Embed(
            title="Conta Criada com Sucesso!",
            description=f"Bem-vindo(a), **{interaction.user.display_name}**!",
            color=discord.Color.green()
        )

        current_time = TimezoneHelper.get_current_time(selected_timezone)

        embed.add_field(
            name="Suas Informações",
            value=(
                f"**Gênero:** {Gender.get_label(selected_gender)}\n"
                f"**Fuso Horário:** {selected_timezone}\n"
                f"**Hora Atual:** {current_time}"
            ),
            inline=False
        )

        embed.add_field(
            name="Próximos Passos",
            value=(
                "Use `.help` para ver os comandos disponíveis!\n"
                "Use `.profile` para ver seu perfil!"
            ),
            inline=False
        )

        embed.set_footer(text="Boa sorte na sua jornada Pokémon!")

        await interaction.followup.send(
            embed=embed,
            view=None
        )

class TimezoneTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="🇧🇷 Brasil",
                value="br",
                description="Fusos horários do Brasil"
            ),
            discord.SelectOption(
                label="🌎 Outros",
                value="other",
                description="Fusos horários internacionais"
            )
        ]
        
        super().__init__(
            placeholder="Escolha a região do fuso horário...",
            options=options,
            custom_id="timezone_type_select",
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction):
        for item in self.view.children:
            if isinstance(item, TimezoneSelect):
                self.view.remove_item(item)
        
        new_select = TimezoneSelect(self.values[0])
        new_select.disabled = False
        self.view.add_item(new_select)
        self.disabled = True
        
        await interaction.response.edit_message(
            content=(
                f"✅ Gênero selecionado: **{Gender.get_label(self.view.selected_gender)}**\n"
                f"✅ Região selecionada: **{'Brasil' if self.values[0] == 'br' else 'Internacional'}**\n\n"
                f"Agora selecione seu fuso horário:"
            ),
            view=self.view
        )

class AccountCreationView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_gender: Optional[str] = None
        self.selected_timezone: Optional[str] = None
        
        self.add_item(GenderSelect())
        self.add_item(TimezoneTypeSelect())
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            return False
        return True
