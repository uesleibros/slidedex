import discord
import sys

emoji_cache: dict[str, int] = {}

async def load_application_emojis(bot: discord.Client) -> None:
	emoji_cache.clear()
	for e in await bot.fetch_application_emojis():
		emoji_cache[sys.intern(e.name)] = e.id
	print(f"🔄 Carregados {len(emoji_cache)} application emojis")

def get_app_emoji(name: str) -> str:
	eid = emoji_cache.get(name)
	if eid is None:
		return ""
	return f"<:{name}:{eid}>"