import io
import random
import discord
from discord.ext import commands
from curl_cffi import requests
from PIL import Image
from typing import Optional
from utils.pokemon_emojis import get_app_emoji

class Spawn(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.backgrounds = {
			"grassland": "resources/backgrounds/route.jpg",
			"forest": "resources/backgrounds/forest.jpg",
			"cave": "resources/backgrounds/cave.jpg",
			"mountain": "resources/backgrounds/cave.jpg",
			"sea": "resources/backgrounds/sea.jpg",
			"urban": "resources/backgrounds/urban.png",
			"rare": "resources/backgrounds/rare.png",
			"rough-terrain": "resources/backgrounds/rough_terrain.png",
			"waters-edge": "resources/backgrounds/beach.png"
		}
		self.preloaded_backgrounds = {}
		for key, path in self.backgrounds.items():
			self.preloaded_backgrounds[key] = Image.open(path).convert("RGBA").resize((400, 225), Image.Resampling.NEAREST)

	@commands.command(name="spawn", aliases=["sp"])
	async def spawn_command(self, ctx: commands.Context, pokemon_query: Optional[str] = None) -> None:
		is_shiny = False

		if not pokemon_query:
			pokemon_query =  str(random.randint(1, 386))

		if "=shiny" in pokemon_query.lower():
			is_shiny = True
			pokemon_query = pokemon_query.replace("=shiny", "").strip()

		async with requests.AsyncSession() as session:
			resp = await session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_query.lower()}")
			data = resp.json()
			name = data["name"].capitalize()
			if is_shiny:
				sprite_url = data["sprites"]["front_shiny"]
			else:
				sprite_url = data["sprites"]["front_default"]

			if not sprite_url:
				is_shiny = False
				sprite_url = data["sprites"]["front_default"]

			species_resp = await session.get(f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_query.lower()}")
			species_data = species_resp.json()
			is_legendary = species_data.get("is_legendary", False)
			is_mythical = species_data.get("is_mythical", False)
			pokemon_emoji = get_app_emoji(f"p_{data['id']}")
			habitat_name = species_data["habitat"]["name"] if species_data["habitat"] else ("rare" if (is_legendary or is_mythical) else "grassland")
			
			sprite_task = session.get(sprite_url)
			sprite_resp = await sprite_task
			sprite_bytes = sprite_resp.content

		sprite_img = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA").resize((200, 200), Image.Resampling.NEAREST)
		background = self.preloaded_backgrounds[habitat_name].copy()
		bg_w, bg_h = background.size
		sp_w, sp_h = sprite_img.size
		position = ((bg_w - sp_w) // 2, bg_h - sp_h - 10)
		background.paste(sprite_img, position, sprite_img)

		with io.BytesIO() as image_binary:
			background.save(image_binary, "PNG")
			image_binary.seek(0)
			file = discord.File(fp=image_binary, filename="spawn.png")

		title = "✨ Um Pokémon Shiny Selvagem Apareceu! ✨" if is_shiny else "Um Pokémon Selvagem Apareceu!"
		desc = f"Olha só quem surgiu: {pokemon_emoji} **{name}**{' SHINY' if is_shiny else ''}!"
		embed = discord.Embed(
			title=title,
			description=desc,
			color=discord.Color.gold() if is_shiny else discord.Color.green()
		)
		embed.set_image(url="attachment://spawn.png")
		await ctx.send(embed=embed, file=file)

async def setup(bot: commands.Bot):
	await bot.add_cog(Spawn(bot))
