import discord
from discord.ext import commands

class EventHandler:
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	async def on_ready(self) -> None:
		print(f"{self.bot.user} online")
	
	async def on_message(self, message: discord.Message) -> None:
		if message.author.bot:
			return
		
		if self._is_mention_only(message):
			await self._send_prefix_info(message)
		
		await self.bot.process_commands(message)
	
	def _is_mention_only(self, message: discord.Message) -> bool:
		if not self.bot.user:
			return False
			
		if not self.bot.user.mentioned_in(message) or message.mention_everyone:
			return False
		
		return message.content.strip() in [
			f'<@{self.bot.user.id}>', 
			f'<@!{self.bot.user.id}>'
		]
	
	async def _send_prefix_info(self, message: discord.Message) -> None:
		prefix = self.bot.command_prefix
		await message.channel.send(
			f"Olá {message.author.mention}! Meu prefixo é `{prefix}`\n"
			f"Use `{prefix}help` para ver todos os comandos!"
		)