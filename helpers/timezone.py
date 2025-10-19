from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

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
			timezone = ZoneInfo(tz)
			now = datetime.now(timezone)
			return now.strftime("%H:%M")
		except Exception:
			return "00:00"
	
	@classmethod
	def get_label(cls, tz: str) -> str:
		tz_map = cls._get_timezone_map()
		return tz_map.get(tz, tz)
	
	@classmethod
	def convert_to_timezone(cls, dt: datetime | str, tz: str) -> datetime:
		try:
			if isinstance(dt, str):
				dt = datetime.fromisoformat(dt)
			
			if dt.tzinfo is None:
				dt = dt.replace(tzinfo=ZoneInfo('UTC'))
			
			timezone = ZoneInfo(tz)
			return dt.astimezone(timezone)
		except Exception:
			return dt if isinstance(dt, datetime) else datetime.now()

	@classmethod
	def format_datetime(cls, dt: datetime | str, tz: str, fmt: str = '%d/%m/%Y às %H:%M') -> str:
		try:
			if isinstance(dt, str):
				dt = datetime.fromisoformat(dt)
			
			if dt.tzinfo is None:
				dt = dt.replace(tzinfo=ZoneInfo('UTC'))
			
			timezone = ZoneInfo(tz)
			dt_converted = dt.astimezone(timezone)
			return dt_converted.strftime(fmt)
		except Exception:
			if isinstance(dt, datetime):
				return dt.strftime(fmt)
			elif isinstance(dt, str):
				return dt
			return ""