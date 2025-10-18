import discord
import asyncio
import pytz
from typing import Final, Optional
from datetime import datetime

class Gender:
    MALE = "Male"
    FEMALE = "Female"
    
    LABELS: Final[dict[str, str]] = {
        MALE: "♂️ Masculino",
        FEMALE: "♀️ Feminino"
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
        ("America/Noronha", "🇧🇷 Fernando de Noronha (UTC-2)"),
        ("America/Sao_Paulo", "🇧🇷 São Paulo • Brasília (UTC-3)"),
        ("America/Fortaleza", "🇧🇷 Ceará • Nordeste (UTC-3)"),
        ("America/Recife", "🇧🇷 Pernambuco (UTC-3)"),
        ("America/Belem", "🇧🇷 Pará (UTC-3)"),
        ("America/Manaus", "🇧🇷 Amazonas (UTC-4)"),
        ("America/Cuiaba", "🇧🇷 Mato Grosso (UTC-4)"),
        ("America/Porto_Velho", "🇧🇷 Rondônia (UTC-4)"),
        ("America/Boa_Vista", "🇧🇷 Roraima (UTC-4)"),
        ("America/Rio_Branco", "🇧🇷 Acre (UTC-5)"),
    )
    
    OTHER_TIMEZONES: Final[tuple[tuple[str, str], ...]] = (
        ("Europe/Lisbon", "🇵🇹 Portugal (UTC+0)"),
        ("Atlantic/Azores", "🇵🇹 Açores (UTC-1)"),
        ("Africa/Luanda", "🇦🇴 Angola (UTC+1)"),
        ("Africa/Maputo", "🇲🇿 Moçambique (UTC+2)"),
        ("Atlantic/Cape_Verde", "🇨🇻 Cabo Verde (UTC-1)"),
        ("America/New_York", "🇺🇸 Nova York (UTC-5)"),
        ("America/Los_Angeles", "🇺🇸 Los Angeles (UTC-8)"),
        ("America/Chicago", "🇺🇸 Chicago (UTC-6)"),
        ("America/Denver", "🇺🇸 Denver (UTC-7)"),
        ("America/Argentina/Buenos_Aires", "🇦🇷 Argentina (UTC-3)"),
        ("America/Santiago", "🇨🇱 Chile (UTC-3)"),
        ("America/Bogota", "🇨🇴 Colômbia (UTC-5)"),
        ("America/Lima", "🇵🇪 Peru (UTC-5)"),
        ("America/Mexico_City", "🇲🇽 México (UTC-6)"),
        ("Europe/London", "🇬🇧 Reino Unido (UTC+0)"),
        ("Europe/Paris", "🇫🇷 França (UTC+1)"),
        ("Europe/Berlin", "🇩🇪 Alemanha (UTC+1)"),
        ("Europe/Madrid", "🇪🇸 Espanha (UTC+1)"),
        ("Europe/Rome", "🇮🇹 Itália (UTC+1)"),
        ("Europe/Moscow", "🇷🇺 Rússia (UTC+3)"),
        ("Asia/Tokyo", "🇯🇵 Japão (UTC+9)"),
        ("Asia/Shanghai", "🇨🇳 China (UTC+8)"),
        ("Asia/Seoul", "🇰🇷 Coreia do Sul (UTC+9)"),
        ("Asia/Dubai", "🇦🇪 Dubai (UTC+4)"),
        ("Australia/Sydney", "🇦🇺 Austrália (UTC+10)"),
    )
    
    _timezone_map = None
    
    @classmethod
    def _get_timezone_map(cls) -> dict[str, str]:
        if cls._timezone_map is None:
            cls._timezone_map = {}
            for tz_id, label in cls.COMMON_BR_TIMEZONES + cls.OTHER_TIMEZONES:
                cls._timezone_map[tz_id] = label
        return cls._timezone_map
    
    @classmethod
    def get_current_time(cls, tz: str) -> str:
        try:
            timezone = pytz.timezone(tz)
            now = datetime.now(timezone)
            return now.strftime("%H:%M")
        except:
            return "00:00"
    
    @classmethod
    def get_label(cls, tz: str) -> str:
        tz_map = cls._get_timezone_map()
        return tz_map.get(tz, tz)

class AccountCreatedLayout(discord.ui.LayoutView):
    def __init__(self, username: str, gender: str, timezone: str):
        super().__init__()
        
        current_time = TimezoneHelper.get_current_time(timezone)
        timezone_label = TimezoneHelper.get_label(timezone)
        
        container = discord.ui.Container()
        
        container.add_item(discord.ui.TextDisplay("### Conta Criada com Sucesso!"))
        container.add_item(discord.ui.TextDisplay(f"Bem-vindo(a), **{username}**!"))
        container.add_item(discord.ui.Separator())
        
        container.add_item(discord.ui.TextDisplay("-# **Suas Informações**"))
        container.add_item(discord.ui.TextDisplay(
            f"**Gênero:** {Gender.get_label(gender)}\n"
            f"**Fuso Horário:** {timezone_label}\n"
            f"**Hora Atual:** {current_time}"
        ))
        
        container.add_item(discord.ui.Separator())
        
        container.add_item(discord.ui.TextDisplay("-# **Próximos Passos**"))
        container.add_item(discord.ui.TextDisplay(
            "Use `.help` para ver os comandos disponíveis!\n"
            "Use `.profile` para ver seu perfil!"
        ))
        
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay("-# Boa sorte na sua jornada Pokémon!"))
        
        self.add_item(container)

class GenderSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=label[2:],
                value=value,
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

        layout = AccountCreatedLayout(
            username=interaction.user.display_name,
            gender=selected_gender,
            timezone=selected_timezone
        )

        await interaction.followup.send(
            view=layout
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
                f"✅ Região selecionada: **{'🇧🇷 Brasil' if self.values[0] == 'br' else '🌎 Internacional'}**\n\n"
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

