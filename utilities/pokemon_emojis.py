import discord
import sys
from typing import Final

_emoji_cache: dict[str, str] = {}
_EMOJI_FORMAT: Final[str] = "<:{}:{}>"

async def load_application_emojis(bot: discord.Client) -> None:
	global _emoji_cache
	
	emojis = await bot.fetch_application_emojis()
	
	_emoji_cache = {
		sys.intern(e.name): _EMOJI_FORMAT.format(e.name, e.id)
		for e in emojis
	}
	
	print(f"Carregados {len(_emoji_cache)} application emojis")

def get_app_emoji(name: str) -> str:
	return _emoji_cache.get(name, "")