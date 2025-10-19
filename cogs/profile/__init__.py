import discord
import helpers.checks as checks
from cogs.profile.views import ProfileLayoutView
from discord.ext import commands
from utilities.preloaded import preloaded_textures
from utilities.canvas import compose_profile_async
from sdk.toolkit import Toolkit

class Profile(commands.Cog, name="Perfil"):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.tk: Toolkit = Toolkit()

	@commands.command(name="profile", aliases=["pf"])
	@checks.require_account()
	async def profile_command(self, ctx: commands.Context) -> None:
		await ctx.defer()

		uid: str = str(ctx.author.id)
		user: dict = self.tk.users.get(uid)
		user_party: dict = self.tk.pokemon.get_party(uid)
		party_sprites: List[bytes] = []

		for poke in user_party:
			party_sprites.append(self.tk.api.get_pokemon_sprite(poke)[0])

		background = preloaded_textures["profile"]
		buf = await compose_profile_async(party_sprites, background)
		img_file = discord.File(buf, filename="profile.png")
		location_file = discord.File(f"resources/locations/kanto/{user['location']}.png", "location.png")
		pokemon_count: int = self.tk.pokemon.count_all(uid)

		view: discord.ui.LayoutView = ProfileLayoutView(user, pokemon_count)

		await ctx.reply(view=view, files=[img_file, location_file])

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Profile(bot))