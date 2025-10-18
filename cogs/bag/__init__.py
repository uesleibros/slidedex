import discord
import io
import asyncio
from typing import List, Dict, Final
from sdk.toolkit import Toolkit
from discord.ext import commands
from helpers.flags import flags
from sdk.items.constants import ITEM_EMOJIS
from cogs.bag.views import BagItemsLayout
import helpers.checks as checks

class Bag(commands.Cog, name="Mochila"):
    CATEGORY_ICONS: Final[Dict[str, str]] = {
        "pokeballs": "resources/textures/icons/bag/pokeballs.png",
        "berries": "resources/textures/icons/bag/berries.png",
        "tms_hms": "resources/textures/icons/bag/tms_hms.png",
        "key_items": "resources/textures/icons/bag/key_items.png",
        "items": "resources/textures/icons/bag/items.png"
    }
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tk: Toolkit = Toolkit()
        self._icon_cache: Dict[str, bytes] = {}
        self._file_buffers: Dict[str, io.BytesIO] = {}
        self._preload_icons()

    def _preload_icons(self) -> None:
        for category, path in self.CATEGORY_ICONS.items():
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                    self._icon_cache[category] = data
                    self._file_buffers[category] = io.BytesIO(data)
            except FileNotFoundError:
                pass

    def _get_category_files(self) -> List[discord.File]:
        files = []
        for category, buffer in self._file_buffers.items():
            buffer.seek(0)
            files.append(discord.File(buffer, f"{category}.png"))
        return files

    @flags.group(name="bag", invoke_without_command=True)
    @checks.require_account()
    async def bag_root(self, ctx: commands.Context) -> None:
        user_id: str = str(ctx.author.id)
        bag_items = await asyncio.to_thread(self.tk.bag.get_all, user_id)
        
        view = BagItemsLayout(bag_items)
        files = self._get_category_files()
        
        await ctx.message.reply(view=view, files=files)

    @bag_root.command(name="add")
    @checks.require_account()
    async def bag_add_command(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
        user_id: str = str(ctx.author.id)

        try:
            result = await asyncio.to_thread(self.tk.item_service.give, user_id, item_id, quantity)
            emoji = ITEM_EMOJIS.get(result['id'], '❔')
            await ctx.message.reply(
                f"Adicionado {emoji} **{result['name']}** {result['added']}x a sua mochila, contendo **{result['quantity']}x** no total."
            )
        except ValueError as e:
            await ctx.message.reply(str(e))
    
    @bag_root.command(name="remove")
    @checks.require_account()
    async def bag_remove_command(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
        user_id: str = str(ctx.author.id)

        try:
            result_quantity, item_name = await asyncio.gather(
                asyncio.to_thread(self.tk.bag.remove, user_id, item_id, quantity),
                asyncio.to_thread(self.tk.item_service.get_name, item_id)
            )
            emoji = ITEM_EMOJIS.get(item_id, '❔')
            await ctx.message.reply(
                f"Removido {quantity}x {emoji} **{item_name}** da sua mochila, restando **{result_quantity}x** no total."
            )
        except ValueError as e:
            await ctx.message.reply(str(e))

async def setup(bot: commands.Bot):
    await bot.add_cog(Bag(bot))

