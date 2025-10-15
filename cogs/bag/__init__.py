import discord
from typing import List
from sdk.toolkit import Toolkit
from discord.ext import commands
from helpers.flags import flags
from sdk.items.constants import ITEM_EMOJIS
from cogs.bag.views import BagItemsLayout
import helpers.checks as checks

class Bag(commands.Cog, name="Mochila"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.tk: Toolkit = Toolkit()

	@flags.group(name="bag", invoke_without_command=True)
	@checks.require_account()
	async def bag_root(self, ctx: commands.Context) -> None:
		user_id: str = str(ctx.author.id)
		bag_items: List = self.tk.bag.get_all(user_id)

		if not bag_items:
			await ctx.message.reply("Sua mochila está vazia.")
			return
			
		view: discord.ui.LayoutView = BagItemsLayout(bag_items)

		files: List[discord.File] = [
			discord.File("resources/textures/icons/bag/pokeballs.png", "pokeballs.png"),
			discord.File("resources/textures/icons/bag/berries.png", "berries.png"),
			discord.File("resources/textures/icons/bag/tms_hms.png", "tms_hms.png"),
			discord.File("resources/textures/icons/bag/key_items.png", "key_items.png"),
			discord.File("resources/textures/icons/bag/items.png", "items.png")
		]
		await ctx.message.reply(view=view, files=files)

	@bag_root.command(name="add")
	@checks.require_account()
	async def bag_add_command(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
		user_id: str = str(ctx.author.id)

		try:
			result = self.tk.item_service.give(user_id, item_id, quantity)

			await ctx.message.reply(
				f"Adicionado {ITEM_EMOJIS.get(result['id'])} **{result['name']}** {result['added']:>4}x a sua mochila, tendo **{result['quantity']:>4}x** no total."
			)
		except ValueError as e:
			await ctx.message.reply(e)

async def setup(bot: commands.Bot):

	await bot.add_cog(Bag(bot))
