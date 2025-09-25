import discord
import asyncio
import os
import io
from PIL import Image, ImageOps
from curl_cffi import requests
from discord.ext import commands
from dotenv import load_dotenv

async def upload_pokemon_emoji(client: discord.Client, pokemon_name: str, image_url: str, session: requests.AsyncSession):
	try:
		resp = await session.get(image_url)
		if resp.status_code != 200:
			return None

		img_bytes = resp.content
		img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

		bbox = img.getbbox()
		if bbox:
			img = img.crop(bbox)

		img = ImageOps.contain(img, (128, 128), method=Image.Resampling.NEAREST)

		img_buffer = io.BytesIO()
		img.save(img_buffer, format="PNG")
		img_buffer.seek(0)
		
		emoji = await client.create_application_emoji(name=pokemon_name, image=img_buffer.read())
		return emoji.id
	except Exception as e:
		print(f"Erro ao criar {pokemon_name}: {e}")
		return None


async def bulk_upload(client: discord.Client):
	async with requests.AsyncSession() as session:
		tasks = []
		for poke_id in range(1, 387):
			url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-viii/icons/{poke_id}.png"
			tasks.append(upload_pokemon_emoji(client, f"p_{poke_id}", url, session))

		results = await asyncio.gather(*tasks, return_exceptions=True)
		print("Upload finalizado:", results)

load_dotenv()
TOKEN: str = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
	print(f"Logado como {bot.user}")
	await bulk_upload(bot)
	await bot.close()

bot.run(token=TOKEN)