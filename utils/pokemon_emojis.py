import discord

emoji_cache: dict[str, str] = {}

async def load_application_emojis(bot: discord.Client) -> None:
    global emoji_cache
    emojis = await bot.fetch_application_emojis()
    emoji_cache = {e.name: str(e) for e in emojis}
    print(f"🔄 Carregados {len(emoji_cache)} application emojis")

def get_app_emoji(name: str) -> str:
    return emoji_cache.get(name, "")
