import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from utils.pokemon_emojis import load_application_emojis
from utils.preloaded import preload_backgrounds
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

	for filename in os.listdir("./cogs"):
		if filename.endswith(".py") and filename != "__init__.py":
			await bot.load_extension(f"cogs.{filename[:-3]}")
			print(f"📂 Cog carregada: {filename}")

	preload_backgrounds()
	print(f"{bot.user} está online!")

print("oi")
bot.run(token=TOKEN)