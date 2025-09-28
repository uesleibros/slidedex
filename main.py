import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from utils.pokemon_emojis import load_application_emojis
from utils.preloaded import preload_backgrounds, preload_info_backgrounds
from utils.toolkit import Toolkit
from pokemon_sdk import PokemonManager

load_dotenv()
TOKEN: str = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)
toolkit: Toolkit = Toolkit()
pm: PokemonManager

@bot.event
async def on_ready() -> None:
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
	print(f"{bot.user} está online!")

bot.run(token=TOKEN)
