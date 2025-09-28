import discord
from discord.ext import commands
import psutil
import time
import platform
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

    @commands.command(name="botstats", aliases=["bs", "stats"])
    async def botstats_command(self, ctx: commands.Context):
        proc = psutil.Process()
        with proc.oneshot():
            mem_info = proc.memory_full_info()
            cpu_percent = proc.cpu_percent(interval=0.1)
            threads = proc.num_threads()
            handles = proc.num_handles() if hasattr(proc, "num_handles") else "N/A"
            create_time = datetime.utcfromtimestamp(proc.create_time())

        mem_usage = mem_info.rss / 1024**2
        mem_vms = mem_info.vms / 1024**2
        uptime = self.format_uptime()

        total_users = len(self.bot.users)
        latency_ms = round(self.bot.latency  * 1000)
        embed = discord.Embed(
            title="Minhas Estatísticas",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name="⏰ Uptime",
            value=uptime,
            inline=True
        )
        embed.add_field(
            name="🖥️ Plataforma",
            value=f"{platform.system()} {platform.release()} ({platform.machine()})",
            inline=True
        )
        embed.add_field(
            name="⚙️ Python / Discord.py",
            value=f"{platform.python_version()} / {discord.__version__}",
            inline=True
        )

        embed.add_field(
            name="💽 Memória (RSS)",
            value=f"{mem_usage:.2f} MB",
            inline=True
        )
        embed.add_field(
            name="💾 Memória Virtual",
            value=f"{mem_vms:.2f} MB",
            inline=True
        )
        embed.add_field(
            name="🔢 Threads / Handles",
            value=f"{threads} / {handles}",
            inline=True
        )

        embed.add_field(
            name="👥 Usuários únicos",
            value=str(total_users),
            inline=True
        )
        embed.add_field(
            name="📡 Latência",
            value=f"{latency_ms} ms",
            inline=True
        )

        embed.add_field(
            name="🧮 CPU",
            value=f"{cpu_percent:.1f}%",
            inline=True
        )

        embed.set_footer(text=f"uEngine • PID {proc.pid}")

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(BotStats(bot))
