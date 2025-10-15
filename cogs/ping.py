import discord
from discord.ext import commands
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Final
import time
import logging
import asyncio
import psutil
import platform
from datetime import datetime, timedelta

logger: Final = logging.getLogger(__name__)

class LatencyLevel(Enum):
    EXCELLENT = (100, 0x2ecc71, "🟢", "Excelente")
    GOOD = (200, 0xf1c40f, "🟡", "Bom")
    FAIR = (300, 0xe67e22, "🟠", "Regular")
    POOR = (float('inf'), 0xe74c3c, "🔴", "Ruim")
    
    def __init__(self, threshold: float, color: int, emoji: str, label: str):
        self.threshold = threshold
        self.color = color
        self.emoji = emoji
        self.label = label
    
    @classmethod
    def from_latency(cls, latency: float) -> "LatencyLevel":
        for level in cls:
            if latency < level.threshold:
                return level
        return cls.POOR

@dataclass(frozen=True)
class SystemMetrics:
    cpu_usage: float
    memory_usage: float
    memory_total: float
    memory_available: float
    process_memory: float
    thread_count: int
    
    @property
    def memory_percent(self) -> float:
        return round((self.process_memory / self.memory_total) * 100, 2)

@dataclass(frozen=True)
class BotMetrics:
    guild_count: int
    user_count: int
    channel_count: int
    shard_count: Optional[int]
    shard_id: Optional[int]
    uptime: timedelta
    
    @property
    def uptime_formatted(self) -> str:
        days = self.uptime.days
        hours, remainder = divmod(self.uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)

@dataclass(frozen=True)
class PingMetrics:
    websocket: float
    api_latency: float
    database: Optional[float]
    bot_metrics: BotMetrics
    system_metrics: SystemMetrics
    discord_api_version: int
    library_version: str
    python_version: str
    
    @property
    def websocket_level(self) -> LatencyLevel:
        return LatencyLevel.from_latency(self.websocket)
    
    @property
    def api_level(self) -> LatencyLevel:
        return LatencyLevel.from_latency(self.api_latency)
    
    @property
    def database_level(self) -> Optional[LatencyLevel]:
        return LatencyLevel.from_latency(self.database) if self.database else None
    
    @property
    def primary_level(self) -> LatencyLevel:
        avg_latency = (self.websocket + self.api_latency) / 2
        return LatencyLevel.from_latency(avg_latency)

class Utility(commands.Cog, name="Utilidade"):
    MEASUREMENT_TIMEOUT: Final[float] = 10.0
    API_SAMPLES: Final[int] = 3
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process = psutil.Process()
        self.start_time = datetime.utcnow()
    
    @commands.command(name="ping", aliases=["latency"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def ping(self, ctx: commands.Context) -> None:
        try:
            metrics = await asyncio.wait_for(
                self._measure_all_metrics(ctx),
                timeout=self.MEASUREMENT_TIMEOUT
            )
            
            embed = self._build_embed(metrics)
            await ctx.reply(embed=embed, mention_author=False)
            
            logger.info(
                f"Ping executado | User: {ctx.author.id} | Guild: {ctx.guild.id if ctx.guild else 'DM'} | "
                f"WS: {metrics.websocket}ms | API: {metrics.api_latency}ms | "
                f"DB: {metrics.database}ms" if metrics.database else ""
            )
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout na medição de latência | "
                f"Guild: {ctx.guild.id if ctx.guild else 'DM'} | "
                f"User: {ctx.author.id}"
            )
            await self._send_error(ctx, "Tempo esgotado ao medir a latência.")
            
        except discord.Forbidden:
            logger.error(
                f"Permissões insuficientes | "
                f"Guild: {ctx.guild.id if ctx.guild else 'DM'}"
            )
            
        except Exception as e:
            logger.error(
                f"Erro no comando ping | User: {ctx.author.id} | Error: {type(e).__name__}: {e}",
                exc_info=True
            )
            await self._send_error(ctx, "Erro ao processar o comando.")
    
    async def _measure_all_metrics(self, ctx: commands.Context) -> PingMetrics:
        websocket_latency = self._get_websocket_latency()
        api_latency = await self._measure_api_latency()
        database_latency = await self._measure_database()
        bot_metrics = self._collect_bot_metrics(ctx)
        system_metrics = self._collect_system_metrics()
        
        return PingMetrics(
            websocket=websocket_latency,
            api_latency=api_latency,
            database=database_latency,
            bot_metrics=bot_metrics,
            system_metrics=system_metrics,
            discord_api_version=discord.api_version,
            library_version=discord.__version__,
            python_version=platform.python_version()
        )
    
    def _get_websocket_latency(self) -> float:
        latency = self.bot.latency * 1000
        return round(latency, 2) if latency > 0 else 0.0
    
    async def _measure_api_latency(self) -> float:
        latencies = []
        
        for _ in range(self.API_SAMPLES):
            start = time.perf_counter()
            await self.bot.http.get_gateway()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = sum(latencies) / len(latencies)
        return round(avg_latency, 2)
    
    async def _measure_database(self) -> Optional[float]:
        if not hasattr(self.bot, 'pool') or not self.bot.pool:
            return None
        
        try:
            start = time.perf_counter()
            async with asyncio.timeout(5.0):
                async with self.bot.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            end = time.perf_counter()
            return round((end - start) * 1000, 2)
            
        except Exception as e:
            logger.error(f"Erro ao medir latência do database: {type(e).__name__}: {e}")
            return None
    
    def _collect_bot_metrics(self, ctx: commands.Context) -> BotMetrics:
        guild_count = len(self.bot.guilds)
        user_count = len(self.bot.users)
        channel_count = sum(len(guild.channels) for guild in self.bot.guilds)
        shard_count = self.bot.shard_count if self.bot.shard_count else None
        shard_id = ctx.guild.shard_id if ctx.guild else None
        uptime = datetime.utcnow() - self.start_time
        
        return BotMetrics(
            guild_count=guild_count,
            user_count=user_count,
            channel_count=channel_count,
            shard_count=shard_count,
            shard_id=shard_id,
            uptime=uptime
        )
    
    def _collect_system_metrics(self) -> SystemMetrics:
        memory = psutil.virtual_memory()
        
        with self.process.oneshot():
            cpu_usage = self.process.cpu_percent()
            process_memory = self.process.memory_info().rss / 1024 / 1024
            thread_count = self.process.num_threads()
        
        return SystemMetrics(
            cpu_usage=round(cpu_usage, 2),
            memory_usage=round(memory.percent, 2),
            memory_total=round(memory.total / 1024 / 1024, 2),
            memory_available=round(memory.available / 1024 / 1024, 2),
            process_memory=round(process_memory, 2),
            thread_count=thread_count
        )
    
    def _build_embed(self, metrics: PingMetrics) -> discord.Embed:
        level = metrics.primary_level
        
        embed = discord.Embed(
            title="🏓 Pong! Status do Sistema",
            color=level.color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="📡 Latência WebSocket",
            value=f"`{metrics.websocket}ms` {metrics.websocket_level.emoji}",
            inline=True
        )
        
        embed.add_field(
            name="🌐 Latência API Discord",
            value=f"`{metrics.api_latency}ms` {metrics.api_level.emoji}",
            inline=True
        )
        
        if metrics.database is not None:
            embed.add_field(
                name="💾 Latência Database",
                value=f"`{metrics.database}ms` {metrics.database_level.emoji}",
                inline=True
            )
        
        bot_info = (
            f"**Servidores:** `{metrics.bot_metrics.guild_count:,}`\n"
            f"**Usuários:** `{metrics.bot_metrics.user_count:,}`\n"
            f"**Canais:** `{metrics.bot_metrics.channel_count:,}`\n"
            f"**Uptime:** `{metrics.bot_metrics.uptime_formatted}`"
        )
        
        if metrics.bot_metrics.shard_count:
            bot_info += f"\n**Shards:** `{metrics.bot_metrics.shard_count}`"
        if metrics.bot_metrics.shard_id is not None:
            bot_info += f"\n**Shard Atual:** `#{metrics.bot_metrics.shard_id}`"
        
        embed.add_field(
            name="🤖 Informações do Bot",
            value=bot_info,
            inline=True
        )
        
        system_info = (
            f"**CPU:** `{metrics.system_metrics.cpu_usage}%`\n"
            f"**RAM (Bot):** `{metrics.system_metrics.process_memory:.2f}MB` "
            f"(`{metrics.system_metrics.memory_percent}%`)\n"
            f"**RAM (Sistema):** `{metrics.system_metrics.memory_usage}%` "
            f"(`{metrics.system_metrics.memory_available:.0f}MB` livre)\n"
            f"**Threads:** `{metrics.system_metrics.thread_count}`"
        )
        
        embed.add_field(
            name="💻 Sistema",
            value=system_info,
            inline=True
        )
        
        technical_info = (
            f"**Python:** `{metrics.python_version}`\n"
            f"**Discord.py:** `{metrics.library_version}`\n"
            f"**API Version:** `v{metrics.discord_api_version}`\n"
            f"**Platform:** `{platform.system()} {platform.release()}`"
        )
        
        embed.add_field(
            name="⚙️ Informações Técnicas",
            value=technical_info,
            inline=True
        )
        
        footer_text = f"Status: {level.label} {level.emoji}"
        embed.set_footer(text=footer_text)
        
        return embed
    
    async def _send_error(self, ctx: commands.Context, message: str) -> None:
        try:
            embed = discord.Embed(
                description=message,
                color=0xe74c3c
            )
            await ctx.reply(embed=embed, mention_author=False)
        except discord.HTTPException as e:
            logger.error(f"Falha ao enviar mensagem de erro: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
