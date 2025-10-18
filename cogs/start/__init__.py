import discord
import helpers.checks as checks
from cogs.start.views import AccountCreationView
from discord.ext import commands

class Start(commands.Cog, name="Começar"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.cooldown(1, 10, commands.BucketType.user)
	@commands.command(name="start")
	@checks.require_no_account()
	async def start_command(self, ctx: commands.Context):
		user_id: str = str(ctx.author.id)
		view = AccountCreationView(user_id)

		await ctx.reply(f"Vamos criar a sua conta!", view=view)

async def setup(bot: commands.Bot):
	await bot.add_cog(Start(bot))
