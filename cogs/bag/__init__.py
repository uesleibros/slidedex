import discord
from discord.ext import commands

class Bag(commands.Cog, name="Mochila"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.command(name="bag")
	async def bag_command(self, ctx: commands.Context):
		await ctx.message.reply("oi")

async def setup(bot: commands.Bot):
	await bot.add_cog(Bag(bot))