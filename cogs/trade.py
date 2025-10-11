import discord
from discord.ext import commands
from typing import Optional
from helpers.checks import requires_account
from pokemon_sdk.trade.views import TradeView, TradeRequestView
from pokemon_sdk.config import pm, tm, tk

class Trade(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	@commands.group(name="trade", aliases=["t"], invoke_without_command=True)
	@requires_account()
	async def trade(self, ctx: commands.Context, user: Optional[discord.Member] = None):
		if not user:
			return await ctx.send(
				"Mencione um usuário para trocar!\n"
				"Uso: `.trade @usuário`"
			)
		
		if user.bot:
			return await ctx.send("Você não pode trocar com bots!")
		
		if user.id == ctx.author.id:
			return await ctx.send("Você não pode trocar consigo mesmo!")
		
		initiator_id = str(ctx.author.id)
		partner_id = str(user.id)
		
		try:
			tk.get_user(partner_id)
		except ValueError:
			return await ctx.send(f"{user.mention} ainda não tem uma conta!")
		
		if tm.is_trading(initiator_id):
			return await ctx.send("Você já está em uma trade ativa!")
		
		if tm.is_trading(partner_id):
			return await ctx.send(f"{user.mention} já está em uma trade ativa!")
		
		request_view = TradeRequestView(ctx.author, user, timeout=60.0)
		
		request_embed = discord.Embed(
			title="Solicitação de Trade",
			description=f"{ctx.author.mention} quer trocar com {user.mention}!",
			color=discord.Color.blue()
		)
		request_embed.add_field(
			name="Aguardando Confirmação",
			value=f"{user.mention}, clique em **Aceitar** para iniciar a trade ou **Recusar** para cancelar.",
			inline=False
		)
		request_embed.set_footer(text="Esta solicitação expira em 60 segundos")
		
		request_message = await ctx.send(embed=request_embed, view=request_view)
		request_view.message = request_message
		
		await request_view.wait()
		
		if not request_view.accepted:
			return
		
		try:
			trade = tm.create_trade(initiator_id, partner_id)
		except ValueError as e:
			return await ctx.send(f"{str(e)}")
		
		view = TradeView(tm, trade)
		
		embed = await view._create_trade_embed()
		
		message = await ctx.send(
			content=f"{ctx.author.mention} ↔️ {user.mention}",
			embed=embed,
			view=view
		)
		
		view.message = message
		trade.message = message
		trade.channel_id = ctx.channel.id
	
	@trade.command(name="add", aliases=["a"])
	@requires_account()
	async def trade_add(self, ctx: commands.Context, type: str, *args):
		user_id = str(ctx.author.id)
		
		trade = tm.get_active_trade(user_id)
		if not trade:
			return await ctx.send("Você não está em uma trade ativa!")
		
		type = type.lower()
		
		if type in ["pokemon", "p", "poke"]:
			if not args:
				return await ctx.send("Especifique os IDs dos Pokémon!\nExemplo: `.trade add pokemon 1 5 23`")
			
			try:
				pokemon_ids = [int(arg) for arg in args]
			except ValueError:
				return await ctx.send("IDs inválidos! Use apenas números.")
			
			success, error = tm.add_pokemon_to_offer(trade.trade_id, user_id, pokemon_ids)
			
			if not success:
				return await ctx.send(f"{error}")
			
			await ctx.send(f"{len(pokemon_ids)} Pokémon adicionado(s) à sua oferta!")
		
		elif type in ["item", "i", "items"]:
			if not args:
				return await ctx.send("Especifique o item!\nExemplo: `.trade add item rare-candy 5`")
			
			item_id = args[0].lower()
			quantity = 1
			
			if len(args) > 1:
				try:
					quantity = int(args[1])
				except ValueError:
					return await ctx.send("Quantidade inválida!")
			
			success, error = tm.add_items_to_offer(
				trade.trade_id,
				user_id,
				{item_id: quantity}
			)
			
			if not success:
				return await ctx.send(f"{error}")
			
			item_name = pm.get_item_name(item_id)
			await ctx.send(f"**{item_name}** x{quantity} adicionado à sua oferta!")
		
		elif type in ["money", "m", "cash"]:
			if not args:
				return await ctx.send("Especifique a quantidade!\nExemplo: `.trade add money 5000`")
			
			try:
				amount = int(args[0])
			except ValueError:
				return await ctx.send("Quantidade inválida!")
			
			success, error = tm.set_money_offer(trade.trade_id, user_id, amount)
			
			if not success:
				return await ctx.send(f"{error}")
			
			await ctx.send(f"₽{amount:,} adicionado à sua oferta!")
		
		else:
			return await ctx.send(
				"Tipo inválido!\n"
				"Use: `pokemon`, `item` ou `money`"
			)
		
		if trade.message:
			view = TradeView(tm, trade)
			view.message = trade.message
			await view.update_embed()
	
	@trade.command(name="remove", aliases=["r"])
	@requires_account()
	async def trade_remove(self, ctx: commands.Context, type: str, *args):
		user_id = str(ctx.author.id)
		
		trade = tm.get_active_trade(user_id)
		if not trade:
			return await ctx.send("Você não está em uma trade ativa!")
		
		type = type.lower()
		
		if type in ["pokemon", "p", "poke"]:
			if not args:
				return await ctx.send("Especifique os IDs dos Pokémon!")
			
			try:
				pokemon_ids = [int(arg) for arg in args]
			except ValueError:
				return await ctx.send("IDs inválidos!")
			
			tm.remove_pokemon_from_offer(trade.trade_id, user_id, pokemon_ids)
			await ctx.send(f"{len(pokemon_ids)} Pokémon removido(s)!")
		
		elif type in ["item", "i"]:
			if not args:
				return await ctx.send("Especifique o item!")
			
			item_id = args[0].lower()
			quantity = 999999
			
			if len(args) > 1:
				try:
					quantity = int(args[1])
				except ValueError:
					pass
			
			tm.remove_items_from_offer(
				trade.trade_id,
				user_id,
				{item_id: quantity}
			)
			
			item_name = pm.get_item_name(item_id)
			await ctx.send(f"**{item_name}** removido!")
		
		elif type in ["money", "m"]:
			await tm.set_money_offer(trade.trade_id, user_id, 0)
			await ctx.send("Dinheiro removido da oferta!")
		
		if trade.message:
			view = TradeView(tm, trade)
			view.message = trade.message
			await view.update_embed()
	
	@trade.command(name="cancel", aliases=["c"])
	@requires_account()
	async def trade_cancel(self, ctx: commands.Context):
		user_id = str(ctx.author.id)
		
		trade = tm.get_active_trade(user_id)
		if not trade:
			return await ctx.send("Você não está em uma trade ativa!")
		
		tm.cancel_trade(trade.trade_id)
		await ctx.send("Trade cancelada!")
	
	@trade.command(name="info", aliases=["i"])
	@requires_account()
	async def trade_info(self, ctx: commands.Context):
		user_id = str(ctx.author.id)
		
		trade = tm.get_active_trade(user_id)
		if not trade:
			return await ctx.send("Você não está em uma trade ativa!")
		
		view = TradeView(tm, trade)
		embed = await view._create_trade_embed()
		
		await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
	await bot.add_cog(Trade(bot))
