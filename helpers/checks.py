import discord
from functools import wraps
from discord.ext import commands

def requires_account():
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx: commands.Context, *args, **kwargs):
			from __main__ import toolkit
			
			user_id = str(ctx.author.id)
			user = toolkit.get_user(user_id)
			
			if not user:
				await ctx.send("Você ainda não tem uma conta!\nUse `.start` para começar sua jornada Pokémon!")
				return
			
			return await func(self, ctx, *args, **kwargs)
		return wrapper
	return decorator