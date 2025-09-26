import io
import random
import discord
from discord.ext import commands
from curl_cffi import requests
from PIL import Image
from typing import Optional

from utils.preloaded import preloaded_backgrounds
from utils.pokemon_emojis import get_app_emoji
from utils.spawn_text import get_spawn_text
from utils.calculations import generate_stats
from utils.generators import choose_ability, roll_gender, get_types, select_level_up_moves, choose_held_item

class BattleView(discord.ui.View):
	def __init__(self, author: discord.Member, target_name: str, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.author = author
		self.target_name = target_name

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⚔️")
	async def battle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message(f"{interaction.user.mention} iniciou uma batalha contra **{self.target_name}**!", ephemeral=False)
		for item in self.children:
			item.disabled = True
		await interaction.message.edit(view=self)
		self.stop()

class Spawn(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.preloaded_backgrounds = preloaded_backgrounds

	@commands.command(name="spawn", aliases=["sp"])
	async def spawn_command(self, ctx: commands.Context, pokemon_query: Optional[str] = None) -> None:
		is_shiny = False
		if not pokemon_query:
			pokemon_query = str(random.randint(1, 386))
		if "=shiny" in pokemon_query.lower():
			is_shiny = True
			pokemon_query = pokemon_query.replace("=shiny", "").strip()

		async with requests.AsyncSession() as session:
			resp = await session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_query.lower()}")
			data = resp.json()
			name = data["name"].capitalize()
			if not is_shiny:
				is_shiny = random.randint(1, 8192) == 1
			sprite_url = data["sprites"]["front_shiny"] if is_shiny else data["sprites"]["front_default"]
			if not sprite_url:
				sprite_url = data["sprites"]["front_default"]

			species_resp = await session.get(f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_query.lower()}")
			species_data = species_resp.json()
			is_legendary = species_data.get("is_legendary", False)
			is_mythical = species_data.get("is_mythical", False)
			pokemon_emoji = get_app_emoji(f"p_{data['id']}")
			habitat_name = species_data["habitat"]["name"] if species_data["habitat"] else ("rare" if (is_legendary or is_mythical) else "grassland")
			
			sprite_resp = await session.get(sprite_url)
			sprite_bytes = sprite_resp.content

			base_stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
			level = random.randint(5, 45)
			info = generate_stats(base_stats, level)
			ability = choose_ability(data)
			gender = roll_gender(species_data)
			types = get_types(data)
			moves = select_level_up_moves(data, level)
			held_item = choose_held_item(data)

		sprite_img = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA").resize((200, 200), Image.NEAREST)
		background = self.preloaded_backgrounds[habitat_name].copy()
		position = ((background.width - sprite_img.width) // 2, background.height - sprite_img.height - 10)
		background.paste(sprite_img, position, sprite_img)

		with io.BytesIO() as image_binary:
			background.save(image_binary, "PNG")
			image_binary.seek(0)
			file = discord.File(fp=image_binary, filename="spawn.png")

		title = "✨ Um Pokémon Shiny Selvagem Apareceu! ✨" if is_shiny else "Um Pokémon Selvagem Apareceu!"
		desc = get_spawn_text(habitat_name, f"{pokemon_emoji} **{name}**{' SHINY' if is_shiny else ''}!")

		embed = discord.Embed(
			title=title,
			description=desc,
			color=discord.Color.gold() if is_shiny else discord.Color.green()
		)
		embed.set_image(url="attachment://spawn.png")

		await ctx.send(embed=embed, file=file, view=BattleView(ctx.author, name))

async def setup(bot: commands.Bot):

	await bot.add_cog(Spawn(bot))
