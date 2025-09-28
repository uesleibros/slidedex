import discord
from discord.ext import commands
import psutil, time
import platform
from datetime import datetime, timedelta

class BotStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
    
    def get_uptime(self) -> str:
        delta = timedelta(seconds=int(time.time() - self.start_time))
        days, remainder = divmod(delta.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days: parts.append(f"{int(days)}d")
        if hours: parts.append(f"{int(hours)}h")
        if minutes: parts.append(f"{int(minutes)}m")
        if seconds: parts.append(f"{int(seconds)}s")
        return " ".join(parts)

    @commands.command(name="botstats", aliases=["bs"])
    async def botstats_command(self, ctx: commands.Context):
        proc = psutil.Process()
        mem = proc.memory_full_info().rss / 1024**2
        cpu = psutil.cpu_percent()
        uptime = self.get_uptime()
        
        embed = discord.Embed(
            title="Minhas Estatísticas",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="🖥️ Sistema", value=platform.system(), inline=True)
        embed.add_field(name="💽 Memória", value=f"{mem:.2f} MB", inline=True)
        embed.add_field(name="⚙️ CPU", value=f"{cpu:.1f}%", inline=True)
        embed.add_field(name="⏰ Uptime", value=uptime, inline=True)
        embed.add_field(name="👥 Usuários", value=f"{len(self.bot.users)}", inline=True)
        embed.add_field(name="📡 Latência", value=f"{self.bot.latency*1000:.0f} ms", inline=True)
        embed.set_footer(text=f"Feito por {ctx.bot.user} usando a uEngine.")
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BotStats(bot))
