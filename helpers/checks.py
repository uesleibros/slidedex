import discord
from pokemon_sdk.config import battle_tracker, tk
from functools import wraps
from discord.ext import commands

def not_in_battle():
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx: commands.Context, *args, **kwargs):
			user_id = str(ctx.author.id)
			
			if battle_tracker.is_battling(user_id):
				await ctx.send("Você não pode usar este comando durante uma batalha!")
				return
			
			return await func(self, ctx, *args, **kwargs)
		return wrapper
	return decorator

def requires_battle():
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx: commands.Context, *args, **kwargs):
			user_id = str(ctx.author.id)
			
			if not battle_tracker.is_battling(user_id):
				await ctx.send("Você precisa estar em batalha para usar este comando!")
				return
			
			return await func(self, ctx, *args, **kwargs)
		return wrapper
	return decorator

def requires_account():
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx: commands.Context, *args, **kwargs):
			
			user_id = str(ctx.author.id)
			user = tk.get_user(user_id)
			
			if not user:
				await ctx.send("Você ainda não tem uma conta!\nUse `.start` para começar sua jornada Pokémon!")
				return
			
			return await func(self, ctx, *args, **kwargs)
		return wrapper

	return decorator
