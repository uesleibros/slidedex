import os
import discord
from typing import Optional
from discord.ext import commands
from dotenv import load_dotenv
from utils.pokemon_emojis import load_application_emojis
from utils.preloaded import preload_backgrounds, preload_info_backgrounds, preload_textures
from utils.toolkit import Toolkit
from pokemon_sdk import PokemonManager

load_dotenv()
TOKEN: Optional[str] = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
toolkit = Toolkit()
pm: PokemonManager | None = None

@bot.event
async def on_ready():
	global pm
	pm = PokemonManager(toolkit)
	await load_application_emojis(bot)

	for root, _, files in os.walk("./cogs"):
		for filename in files:
			if filename.endswith(".py") and filename != "__init__.py":
				rel_path = os.path.relpath(os.path.join(root, filename), "./cogs")
				module = "cogs." + rel_path.replace(os.sep, ".")[:-3]

				await bot.load_extension(module)
				print(f"📂 Cog carregada: {module}")

	preload_backgrounds()
	preload_info_backgrounds()
	preload_textures()
	print(f"{bot.user} online")


bot.run(str(TOKEN))

