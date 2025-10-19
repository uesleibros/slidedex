import discord
import helpers.checks as checks
from cogs.profile.views import ProfileLayoutView
from discord.ext import commands
from utilities.preloaded import preloaded_textures
from utilities.canvas import compose_profile_async
from sdk.toolkit import Toolkit
from sdk.constants import CURRENT_REGION

class Profile(commands.Cog, name="Perfil"):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.tk = Toolkit()

	@commands.command(name="profile", aliases=["perfil", "pr", "pf"])
	@checks.require_account()
	async def profile_command(self, ctx: commands.Context) -> None:
		await ctx.defer()

		uid = str(ctx.author.id)
		tk = self.tk
		
		user: dict = tk.users.get(uid)
		party_sprites = [tk.api.get_pokemon_sprite(p)[0] for p in tk.pokemon.get_party(uid)]
		
		buf = await compose_profile_async(party_sprites, preloaded_textures["profile"])
		
		files = [
			discord.File(buf, filename="profile.png"),
			discord.File(f"resources/textures/trainer_{user['gender'].lower()}.png", "trainer.png"),
			discord.File(f"resources/locations/{CURRENT_REGION}/{user['location']}.png", "location.png")
		]
		
		await ctx.reply(
			view=ProfileLayoutView(user, tk.pokemon.count_all(uid)),
			files=files
		)

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Profile(bot))