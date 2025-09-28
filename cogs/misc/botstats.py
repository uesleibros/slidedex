import discord
from discord.ext import commands
import psutil
import time
import platform
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io

def _make_stats_chart(cpu, ram, latency):
	w, h = 580, 220
	img = Image.new("RGBA", (w, h), (25, 25, 35, 255))
	draw = ImageDraw.Draw(img)
	
	try:
		font = ImageFont.truetype("resources/fonts/DejaVuSans.ttf", 18)
		font_small = ImageFont.truetype("resources/fonts/DejaVuSans.ttf", 14)
	except:
		font = ImageFont.load_default()
		font_small = ImageFont.load_default()

	stats = [
		("CPU %", cpu, 100, 70, 90),
		("RAM MB", ram, 600, 300, 600),
		("Latência ms", latency, 300, 150, 300),
	]

	y = 30
	for label, val, limit, warn, crit in stats:
		ratio = min(val / limit, 1.0) if limit > 0 else 0
		bar_x, bar_y = 170, y
		bar_w, bar_h = 300, 24
		filled_w = int(bar_w * ratio)

		if val >= crit:
			color, status = (230, 60, 60), "CRÍTICO"
		elif val >= warn:
			color, status = (230, 200, 60), "ALERTA"
		else:
			color, status = (60, 200, 100), "OK"

		draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=(60, 60, 80), outline=(90, 90, 120))
		draw.rectangle([bar_x, bar_y, bar_x + filled_w, bar_y + bar_h], fill=color)

		bbox = font.getbbox(label)
		draw.text((20, bar_y + (bar_h - bbox[3]) // 2), label, fill=(230, 230, 230), font=font)

		val_text = f"{val:.1f}/{limit}"
		bbox_val = font_small.getbbox(val_text)
		draw.text((bar_x + bar_w + 15, bar_y + (bar_h - bbox_val[3]) // 2), val_text, fill=(220, 220, 220), font=font_small)

		bbox_status = font_small.getbbox(status)
		status_x = bar_x + (bar_w - bbox_status[2]) // 2
		status_y = bar_y + (bar_h - bbox_status[3]) // 2
		draw.text((status_x, status_y), status, fill=(255, 255, 255), font=font_small)

		y += 60

	buf = io.BytesIO()
	img.save(buf, format="PNG", optimize=False, compress_level=1)
	buf.seek(0)
	return buf

async def make_stats_chart_async(*args, **kwargs):
	return await asyncio.to_thread(_make_stats_chart, *args, **kwargs)

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

		buf = await make_stats_chart_async(cpu_percent, mem_usage, latency_ms)
		file = discord.File(buf, filename="stats.png")
		embed.set_image(url="attachment://stats.png")
		await ctx.send(embed=embed, file=file)


async def setup(bot: commands.Bot):
	await bot.add_cog(BotStats(bot))
