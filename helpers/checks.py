from functools import wraps
from discord.ext import commands
from sdk.toolkit import Toolkit

def require_no_account():
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx: commands, *args, **kwargs):
			tk: Toolkit = Toolkit()

			user_id: str = str(ctx.author.id)
			user = tk.users.get(user_id)
			if user:
				await ctx.send(f"Esse comando só pode ser usado por quem não tem conta.")
				return

			return await func(self, ctx, *args, **kwargs)
		return wrapper
	return decorator

def require_account():
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx: commands, *args, **kwargs):
			tk: Toolkit = Toolkit()

			user_id: str = str(ctx.author.id)
			user = tk.users.get(user_id)
			if not user:
				await ctx.send(f"Você ainda não tem uma conta!\nUse `.start` para começar sua jornada Pokémon!")
				return

			return await func(self, ctx, *args, **kwargs)
		return wrapper
	return decorator