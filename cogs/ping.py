import discord
from discord.ext import commands
from dataclasses import dataclass
from enum import Enum
import time

class LatencyLevel(Enum):
	EXCELLENT = (100, discord.Color.green(), "🟢")
	GOOD = (200, discord.Color.yellow(), "🟡")
	POOR = (float('inf'), discord.Color.red(), "🔴")
	
	def __init__(self, threshold: float, color: discord.Color, emoji: str):
		self.threshold = threshold
		self.color = color
		self.emoji = emoji
	
	@classmethod
	def from_latency(cls, latency: float) -> "LatencyLevel":
		for level in cls:
			if latency < level.threshold:
				return level
		return cls.POOR

@dataclass(frozen=True)
class PingMetrics:
	websocket: float
	api: float
	
	@property
	def level(self) -> LatencyLevel:
		return LatencyLevel.from_latency(self.websocket)

class Utility(commands.Cog, name="Utilidade"):	
	def __init__(self, bot: commands.Bot):
		self.bot = bot
	
	@commands.command(name="ping", aliases=["latency"])
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def ping(self, ctx: commands.Context) -> None:
		metrics = await self._measure_latency(ctx)
		embed = self._build_embed(metrics)
		await ctx.message.reply(embed=embed)
	
	async def _measure_latency(self, ctx: commands.Context) -> PingMetrics:
		start = time.perf_counter()
		await ctx.typing()
		end = time.perf_counter()
		
		websocket = round(self.bot.latency * 1000, 2)
		api = round((end - start) * 1000, 2)
		
		return PingMetrics(websocket=websocket, api=api)
	
	def _build_embed(self, metrics: PingMetrics) -> discord.Embed:
		level = metrics.level
		
		embed = discord.Embed(
			title="🏓 Pong!",
			color=level.color
		)
		
		embed.add_field(
			name="Websocket",
			value=f"`{metrics.websocket}ms` {level.emoji}",
			inline=True
		)
		
		embed.add_field(
			name="API",
			value=f"`{metrics.api}ms`",
			inline=True
		)
		
		return embed

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Utility(bot))
