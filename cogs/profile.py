import discord
from typing import List, Optional
from __main__ import pm
from discord.ext import commands
from utils.preloaded import preloaded_textures
from utils.canvas import compose_profile_async
from helpers.checks import requires_account

class Profile(commands.Cog):
	""" Comandos relacionados a perfil. """
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name="profile", aliases=["pf", "prof", "pfl"])
	@requires_account()
	async def profile_command(self, ctx: commands.Context, user: Optional[discord.Member]) -> None:
		user = ctx.author if not user else user
		user_info = pm.tk.get_user(str(user.id))

		user_party = pm.tk.get_user_party(str(user.id))
		user_pokemon = pm.tk.get_user_pokemon(str(user.id))
		party_sprites: List[bytes] = []

		for poke in user_party:
			party_sprites.append(pm.service.get_pokemon_sprite(poke)[0])

		background = preloaded_textures["profile"]
		buf = await compose_profile_async(party_sprites, background)
		img_file = discord.File(buf, filename="profile.png")

		embed = discord.Embed(
			title=f"Perfil de {user.display_name}"
		)

		embed.add_field(name="₽ Dinheiro", value=f"{user_info['money']:,.2f}")
		embed.add_field(name="<:pokeball:1424443006626431109> Pokémon", value=f"{len(user_pokemon)}x")
		embed.add_field(name="<:seed:1426286504694648882> Seed", value=pm.tk.get_user_seed(str(user.id)))
		
		del user_pokemon
		del user_party
		del party_sprites

		embed.set_image(url="attachment://profile.png")
		await ctx.send(embed=embed, file=img_file)

async def setup(bot: commands.Bot):
	await bot.add_cog(Profile(bot))
