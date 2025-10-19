from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

class TimezoneHelper:
	COMMON_BR_TIMEZONES: Final[tuple[tuple[str, str], ...]] = (
		("America/Noronha", "Fernando de Noronha (UTC-2)"),
		("America/Sao_Paulo", "Brasília (UTC-3)"),
		("America/Fortaleza", "Ceará (UTC-3)"),
		("America/Recife", "Pernambuco (UTC-3)"),
		("America/Belem", "Pará (UTC-3)"),
		("America/Manaus", "Amazonas (UTC-4)"),
		("America/Cuiaba", "Mato Grosso (UTC-4)"),
		("America/Porto_Velho", "Rondônia (UTC-4)"),
		("America/Boa_Vista", "Roraima (UTC-4)"),
		("America/Rio_Branco", "Acre (UTC-5)"),
	)
	
	OTHER_TIMEZONES: Final[tuple[tuple[str, str], ...]] = (
		("Europe/Lisbon", "Portugal (UTC+0)"),
		("Atlantic/Azores", "Açores (UTC-1)"),
		("Africa/Luanda", "Angola (UTC+1)"),
		("Africa/Maputo", "Moçambique (UTC+2)"),
		("Atlantic/Cape_Verde", "Cabo Verde (UTC-1)"),
		("America/New_York", "Nova York (UTC-5)"),
		("America/Los_Angeles", "Los Angeles (UTC-8)"),
		("America/Chicago", "Chicago (UTC-6)"),
		("America/Denver", "Denver (UTC-7)"),
		("America/Argentina/Buenos_Aires", "Argentina (UTC-3)"),
		("America/Santiago", "Chile (UTC-3)"),
		("America/Bogota", "Colômbia (UTC-5)"),
		("America/Lima", "Peru (UTC-5)"),
		("America/Mexico_City", "México (UTC-6)"),
		("Europe/London", "Reino Unido (UTC+0)"),
		("Europe/Paris", "França (UTC+1)"),
		("Europe/Berlin", "Alemanha (UTC+1)"),
		("Europe/Madrid", "Espanha (UTC+1)"),
		("Europe/Rome", "Itália (UTC+1)"),
		("Europe/Moscow", "Rússia (UTC+3)"),
		("Asia/Tokyo", "Japão (UTC+9)"),
		("Asia/Shanghai", "China (UTC+8)"),
		("Asia/Seoul", "Coreia do Sul (UTC+9)"),
		("Asia/Dubai", "Dubai (UTC+4)"),
		("Australia/Sydney", "Austrália (UTC+10)"),
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
			now = datetime.now(timezone)
			
			dt_date = dt_converted.date()
			now_date = now.date()
			diff_days = (dt_date - now_date).days
			diff_seconds = (dt_converted - now).total_seconds()
			
			date_str = dt_converted.strftime('%d/%m/%Y')
			time_str = dt_converted.strftime('%H:%M')
			hour = dt_converted.hour
			
			def get_period(h: int) -> str:
				if 0 <= h < 6:
					return "madrugada"
				elif 6 <= h < 12:
					return "manhã"
				elif 12 <= h < 18:
					return "tarde"
				else:
					return "noite"
			
			period = get_period(hour)
			
			if diff_days == 0:
				if abs(diff_seconds) < 60:
					return "Agora mesmo"
				elif abs(diff_seconds) < 3600:
					minutes = int(abs(diff_seconds) / 60)
					if diff_seconds < 0:
						return f"Há {minutes} minuto{'s' if minutes > 1 else ''}"
					else:
						return f"Em {minutes} minuto{'s' if minutes > 1 else ''}"
				elif abs(diff_seconds) < 86400:
					hours = int(abs(diff_seconds) / 3600)
					if diff_seconds < 0:
						return f"Há {hours} hora{'s' if hours > 1 else ''} ({date_str}) às {time_str}"
					else:
						return f"Em {hours} hora{'s' if hours > 1 else ''} ({date_str}) às {time_str}"
				else:
					return f"Hoje de {period} ({date_str}) às {time_str}"
			
			elif diff_days == -1:
				return f"Ontem de {period} ({date_str}) às {time_str}"
			elif diff_days == -2:
				return f"Anteontem de {period} ({date_str}) às {time_str}"
			elif diff_days == 1:
				return f"Amanhã de {period} ({date_str}) às {time_str}"
			elif diff_days == 2:
				return f"Depois de amanhã de {period} ({date_str}) às {time_str}"
			
			elif -7 <= diff_days < -2:
				weekdays = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
				weekday_name = weekdays[dt_converted.weekday()]
				return f"{weekday_name.capitalize()} passada ({date_str}) às {time_str}"
			
			elif 2 < diff_days <= 7:
				weekdays = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
				weekday_name = weekdays[dt_converted.weekday()]
				return f"Próxima {weekday_name} ({date_str}) às {time_str}"
			
			elif -14 <= diff_days < -7:
				return f"Semana retrasada ({date_str}) às {time_str}"
			elif 7 < diff_days <= 14:
				return f"Daqui a duas semanas ({date_str}) às {time_str}"
			
			elif -30 <= diff_days < -14:
				weeks = abs(diff_days) // 7
				return f"Há {weeks} semanas ({date_str}) às {time_str}"
			elif 14 < diff_days <= 30:
				weeks = diff_days // 7
				return f"Daqui a {weeks} semanas ({date_str}) às {time_str}"
			
			elif -60 <= diff_days < -30:
				if dt_converted.month == now.month - 1 or (now.month == 1 and dt_converted.month == 12):
					return f"Mês passado ({date_str}) às {time_str}"
				else:
					months_names = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 
					                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
					month_name = months_names[dt_converted.month - 1]
					return f"Em {month_name} ({date_str}) às {time_str}"
			
			elif 30 < diff_days <= 60:
				if dt_converted.month == now.month + 1 or (now.month == 12 and dt_converted.month == 1):
					return f"Próximo mês ({date_str}) às {time_str}"
				else:
					months_names = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 
					                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
					month_name = months_names[dt_converted.month - 1]
					return f"Em {month_name} ({date_str}) às {time_str}"
			
			elif -365 <= diff_days < -60:
				months = abs(diff_days) // 30
				if months == 1:
					return f"Há 1 mês ({date_str}) às {time_str}"
				return f"Há {months} meses ({date_str}) às {time_str}"
			
			elif 60 < diff_days <= 365:
				months = diff_days // 30
				if months == 1:
					return f"Daqui a 1 mês ({date_str}) às {time_str}"
				return f"Daqui a {months} meses ({date_str}) às {time_str}"
			
			elif diff_days < -365:
				years = abs(diff_days) // 365
				if years == 1:
					if dt_converted.year == now.year - 1:
						return f"Ano passado ({date_str}) às {time_str}"
					return f"Há 1 ano ({date_str}) às {time_str}"
				return f"Há {years} anos ({date_str}) às {time_str}"
			
			elif diff_days > 365:
				years = diff_days // 365
				if years == 1:
					if dt_converted.year == now.year + 1:
						return f"Próximo ano ({date_str}) às {time_str}"
					return f"Daqui a 1 ano ({date_str}) às {time_str}"
				return f"Daqui a {years} anos ({date_str}) às {time_str}"
			
			else:
				return dt_converted.strftime(fmt)
				
		except Exception:
			if isinstance(dt, datetime):
				return dt.strftime(fmt)
			elif isinstance(dt, str):
				return dt
			return ""

