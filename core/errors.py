import discord
from discord.ext import commands
from discord.ext.flags import ArgumentParsingError

class ErrorHandler:
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
		handler = self._get_error_handler(error)
		
		if handler:
			await handler(ctx, error)
		else:
			raise error
	
	def _get_error_handler(self, error: commands.CommandError):
		handlers = {
			ArgumentParsingError: self._handle_argument_parsing,
			commands.CommandNotFound: self._handle_command_not_found,
			commands.MissingRequiredArgument: self._handle_missing_argument,
			commands.BadArgument: self._handle_bad_argument,
			commands.CommandOnCooldown: self._handle_cooldown,
			commands.MissingPermissions: self._handle_missing_permissions,
			commands.BotMissingPermissions: self._handle_bot_missing_permissions,
			commands.CheckFailure: self._handle_check_failure,
		}
		
		for error_type, handler in handlers.items():
			if isinstance(error, error_type):
				return handler
		
		return None
	
	async def _handle_argument_parsing(self, ctx: commands.Context, error: ArgumentParsingError) -> None:
		await ctx.send(
			f"Erro nos argumentos: {str(error)}\n"
			f"-# Use `.help {ctx.command.qualified_name}` para ver o uso correto."
		)
	
	async def _handle_command_not_found(self, ctx: commands.Context, error: commands.CommandNotFound) -> None:
		pass
	
	async def _handle_missing_argument(self, ctx: commands.Context, error: commands.MissingRequiredArgument) -> None:
		await ctx.send(
			f"Argumento obrigatório faltando: `{error.param.name}`\n"
			f"-# Use `.help {ctx.command.qualified_name}` para ver o uso correto."
		)
	
	async def _handle_bad_argument(self, ctx: commands.Context, error: commands.BadArgument) -> None:
		await ctx.send(f"Argumento inválido: {str(error)}")
	
	async def _handle_cooldown(self, ctx: commands.Context, error: commands.CommandOnCooldown) -> None:
		await ctx.send(f"Calma! Tente novamente em **{error.retry_after:.1f}s**")
	
	async def _handle_missing_permissions(self, ctx: commands.Context, error: commands.MissingPermissions) -> None:
		await ctx.send("Você não tem permissão para usar este comando!")
	
	async def _handle_bot_missing_permissions(self, ctx: commands.Context, error: commands.BotMissingPermissions) -> None:
		await ctx.send("Eu não tenho permissão para executar este comando!")
	
	async def _handle_check_failure(self, ctx: commands.Context, error: commands.CheckFailure) -> None:
		await ctx.send("Você não pode usar este comando agora.")