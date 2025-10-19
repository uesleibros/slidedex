import discord
import helpers.checks as checks
from discord.ext import commands
from helpers.location import get_location
from sdk.toolkit import Toolkit
from sdk.constants import CURRENT_REGION
from cogs.explore.views import MapLayoutView

class Explore(commands.Cog, name="Exploração"):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.tk: Toolkit = Toolkit()

	@commands.command(name="map", aliases=["mapa", "local"])
	@checks.require_account()
	async def map_command(self, ctx: commands.Context) -> None:
		uid: str = str(ctx.author.id)
		user: dict = self.tk.users.get(uid)
		location: dict = get_location(user["location"])

		location_file = discord.File(f"resources/locations/{CURRENT_REGION}/{user['location']}.png", "location.png")
		view: discord.ui.LayoutView = MapLayoutView(user, location)

		await ctx.reply(view=view, file=location_file)

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Explore(bot))