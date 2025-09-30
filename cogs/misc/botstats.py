import discord
from discord.ext import commands
import psutil
import time
import platform
import asyncio
from datetime import datetime, timedelta

class BotStats(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.start_time = time.time()

	def format_uptime(self) -> str:
		delta = timedelta(seconds=int(time.time() - self.start_time))
		days, remainder = divmod(int(delta.total_seconds()), 86400)
		hours, remainder = divmod(remainder, 3600)
		minutes, seconds = divmod(remainder, 60)
		return f"{days}d {hours}h {minutes}m {seconds}s"

	def classify_status(self, value: float, warn: float, crit: float, unit: str = "") -> str:
		if value >= crit:
			return f"{value:.2f}{unit} [CRÍTICO]"
		elif value >= warn:
			return f"{value:.2f}{unit} [ALERTA]"
		return f"{value:.2f}{unit} [OK]"

	def overall_health(self, statuses):
		if any("[CRÍTICO]" in s for s in statuses):
			return "CRÍTICO"
		elif any("[ALERTA]" in s for s in statuses):
			return "DEGRADADO"
		return "OPERACIONAL"

	def usage_bar(self, value: float, maximum: float, length: int = 12) -> str:
		ratio = max(0.0, min(1.0, (value / maximum) if maximum else 0.0))
		filled = int(round(ratio * length))
		return f"[{'█' * filled}{'░' * (length - filled)}]"

	@commands.command(name="botstats", aliases=["status", "stats", "bs"])
	async def botstats_command(self, ctx: commands.Context):
		proc = psutil.Process()
		with proc.oneshot():
			mem_info = proc.memory_full_info()
			cpu_percent = proc.cpu_percent(interval=0.2)
			threads = proc.num_threads()
			handles = proc.num_handles() if hasattr(proc, "num_handles") else "N/A"
			create_time = datetime.utcfromtimestamp(proc.create_time())

		mem_usage = mem_info.rss / 1024**2
		mem_vms = mem_info.vms / 1024**2
		uptime = self.format_uptime()
		latency_ms = round(self.bot.latency * 1000)

		mem_status = self.classify_status(mem_usage, warn=300, crit=600, unit="MB")
		cpu_status = self.classify_status(cpu_percent, warn=70, crit=90, unit="%")
		latency_status = self.classify_status(latency_ms, warn=150, crit=300, unit="ms")
		overall = self.overall_health([mem_status, cpu_status, latency_status])

		embed = discord.Embed(
			title="Minhas Estatísticas",
			color=discord.Color.blurple()
		)

		embed.add_field(name="Saúde Geral", value=overall, inline=False)

		embed.add_field(name="Tempo em Execução", value=uptime, inline=True)
		embed.add_field(
			name="Plataforma",
			value=f"{platform.system()} {platform.release()} ({platform.machine()})",
			inline=True
		)
		embed.add_field(
			name="Python / discord.py",
			value=f"{platform.python_version()} / {discord.__version__}",
			inline=True
		)

		embed.add_field(
			name="Memória (RSS)",
			value=f"{mem_status}\n{self.usage_bar(mem_usage, 600)}",
			inline=True
		)
		embed.add_field(
			name="Memória (VMS)",
			value=f"{mem_vms:.2f} MB",
			inline=True
		)
		embed.add_field(
			name="Uso de CPU",
			value=f"{cpu_status}\n{self.usage_bar(cpu_percent, 100)}",
			inline=True
		)

		embed.add_field(
			name="Latência",
			value=f"{latency_status}\n{self.usage_bar(latency_ms, 300)}",
			inline=True
		)
		embed.add_field(name="Threads / Handles", value=f"{threads} / {handles}", inline=True)
		embed.add_field(
			name="Processo Iniciado",
			value=create_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
			inline=True
		)

		embed.set_footer(text="Feito com ❤️ usando a uEngine")
		await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
	await bot.add_cog(BotStats(bot))
