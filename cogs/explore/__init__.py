from typing import Optional
import discord
import helpers.checks as checks
from discord.ext import commands
from helpers.location import (
	can_travel, 
	get_location, 
	get_location_name, 
	get_nearby_locations, 
	get_travel_time
)
from sdk.toolkit import Toolkit
from sdk.constants import CURRENT_REGION, TRAVEL_STEP_INTERVAL
from cogs.explore.views import MapLayoutView, TravelSelectView, TravelStatusView

class Explore(commands.Cog, name="Exploração"):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.tk: Toolkit = Toolkit()

	@commands.command(name="map", aliases=["mapa", "local"])
	@checks.require_account()
	async def map_command(self, ctx: commands.Context) -> None:
		uid: str = str(ctx.author.id)
		user: dict = self.tk.users.get(uid)
		
		if self.tk.travel.is_traveling(uid):
			await self._handle_travel_check(ctx, uid, user)
			return
		
		await self._show_map(ctx, user)

	@commands.command(name="travel", aliases=["viajar", "ir", "go"])
	@checks.require_account()
	async def travel_command(self, ctx: commands.Context, *, destination: str = None) -> None:
		uid: str = str(ctx.author.id)
		user: dict = self.tk.users.get(uid)
		
		if self.tk.travel.is_traveling(uid):
			await self._handle_travel_check(ctx, uid, user)
			return
		
		nearby = get_nearby_locations(user['location'])
		
		if not nearby:
			await ctx.reply("Não há localizações próximas disponíveis para viajar.")
			return
		
		destination_id = await self._resolve_destination(ctx, destination, nearby)
		
		if not destination_id:
			return
		
		await self._start_travel(ctx, uid, user, destination_id)

	async def _handle_travel_check(self, ctx: commands.Context, uid: str, user: dict) -> None:
		travel_status = self.tk.travel.get_status(uid)
		
		if not travel_status:
			return
		
		if travel_status['completed']:
			result = self.tk.travel.complete_travel(uid)
			
			if result:
				dest_name = get_location_name(result['destination'])
				steps = result.get('steps_earned', 0)
				
				message = f"Você chegou em **{dest_name}**!"
				
				if steps > 0:
					message += f"\n**Passos ganhos:** {steps}"
				
				message += f"\n\nUse `{ctx.prefix}map` para explorar o local."
				
				await ctx.reply(message)
		else:
			view = TravelStatusView(user, travel_status)
			await ctx.reply(view=view)

	async def _show_map(self, ctx: commands.Context, user: dict) -> None:
		location: dict = get_location(user["location"])
		
		location_file = None
		try:
			location_file = discord.File(
				f"resources/locations/{CURRENT_REGION}/{user['location']}.png", 
				"location.png"
			)
		except FileNotFoundError:
			pass
		
		view = MapLayoutView(user, location)
		
		if location_file:
			await ctx.reply(view=view, file=location_file)
		else:
			await ctx.reply(view=view)

	async def _resolve_destination(
		self, 
		ctx: commands.Context, 
		destination: Optional[str], 
		nearby: list[tuple[str, str, int]]
	) -> Optional[str]:
		if not destination:
			return await self._select_destination_interactive(ctx, nearby)
		
		return self._find_destination_by_name(ctx, destination, nearby)

	async def _select_destination_interactive(
		self, 
		ctx: commands.Context, 
		nearby: list[tuple[str, str, int]]
	) -> Optional[str]:
		view = TravelSelectView(None, nearby)
		
		message = await ctx.reply(
			"**Para onde deseja viajar?**\n"
			"Selecione um destino abaixo:",
			view=view
		)
		
		await view.wait()
		
		if not view.selected_destination:
			await message.edit(
				content="Viagem cancelada por tempo limite.",
				view=None
			)
			return None
		
		dest_name = get_location_name(view.selected_destination)
		await message.edit(
			content=f"**Destino selecionado:** {dest_name}",
			view=None
		)
		
		return view.selected_destination

	def _find_destination_by_name(
		self, 
		ctx: commands.Context, 
		destination: str, 
		nearby: list[tuple[str, str, int]]
	) -> Optional[str]:
		destination_lower = destination.lower()
		
		for dest_id, dest_name, _ in nearby:
			if destination_lower in dest_name.lower() or destination_lower in dest_id:
				return dest_id
		
		return None

	async def _start_travel(
		self, 
		ctx: commands.Context, 
		uid: str, 
		user: dict, 
		destination_id: str
	) -> None:
		can_go, error = can_travel(
			user['location'],
			destination_id,
			user.get('hms', []),
			user.get('badges', []),
			user.get('completed_events', [])
		)
		
		if not can_go:
			await ctx.reply(f"**Acesso negado**\n{error}")
			return
		
		travel_time = get_travel_time(user['location'], destination_id)
		dest_name = get_location_name(destination_id)
		
		self.tk.travel.start_travel(uid, user['location'], destination_id, travel_time, ctx.channel.id)
		
		from helpers.travel import format_time_remaining
		
		time_str = format_time_remaining(travel_time)
		expected_steps = int(travel_time // TRAVEL_STEP_INTERVAL)
		
		message = (
			f"**Viagem iniciada para {dest_name}**\n"
			f"**Tempo estimado:** {time_str}\n"
			f"**Passos esperados:** ~{expected_steps}\n\n"
			f"Use `{ctx.prefix}travel` para ver o progresso da viagem."
		)
		
		await ctx.reply(message)

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Explore(bot))