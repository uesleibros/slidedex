import discord
import aiopoke
from typing import List
from __main__ import pm
from discord.ext import commands
from utils.preloaded import preloaded_textures
from utils.canvas import compose_profile_async
from helpers.checks import requires_account

class Profile(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name="profile", aliases=["pf", "prof", "pfl"])
	@requires_account()
	async def profile_command(self, ctx: commands.Context) -> None:
		user_id: str = str(ctx.author.id)
		user = pm.repo.tk.get_user(user_id)

		user_party = pm.repo.tk.get_user_party(user_id)
		user_pokemon = pm.repo.tk.get_user_pokemon(user_id)
		party_sprites: List[bytes] = []

		for poke in user_party:
			poke_data: aiopoke.Pokemon = await pm.service.get_pokemon(poke["species_id"])
			if poke.get("is_shiny") and poke_data.sprites.front_shiny:
				party_sprites.append(await poke_data.sprites.front_shiny.read())
			elif poke_data.sprites.front_default:
				party_sprites.append(await poke_data.sprites.front_default.read())

		background = preloaded_textures["profile"]
		buf = await compose_profile_async(party_sprites, background)
		img_file = discord.File(buf, filename="profile.png")

		embed = discord.Embed(
			title=f"Perfil de {ctx.author.name}"
		)

		embed.add_field(name="Dinheiro", value=f"${user['money']}")
		embed.add_field(name="Pokémon", value=f"{len(user_pokemon)}")

		del user_pokemon
		del user_party
		del party_sprites

		embed.set_image(url="attachment://profile.png")
		await ctx.send(embed=embed, file=img_file)

async def setup(bot: commands.Bot):
	await bot.add_cog(Profile(bot))