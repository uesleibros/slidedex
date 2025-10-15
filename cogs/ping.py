import discord
from discord.ext import commands
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Final
import time
import logging
import asyncio

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
class PingMetrics:
    websocket: float
    roundtrip: float
    database: Optional[float] = None
    shard_id: Optional[int] = None
    
    @property
    def websocket_level(self) -> LatencyLevel:
        return LatencyLevel.from_latency(self.websocket)
    
    @property
    def roundtrip_level(self) -> LatencyLevel:
        return LatencyLevel.from_latency(self.roundtrip)
    
    @property
    def database_level(self) -> Optional[LatencyLevel]:
        return LatencyLevel.from_latency(self.database) if self.database else None
    
    @property
    def primary_level(self) -> LatencyLevel:
        return self.websocket_level

class Utility(commands.Cog, name="Utilidade"):
    MEASUREMENT_TIMEOUT: Final[float] = 10.0
    MEASUREMENT_RETRIES: Final[int] = 3
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name="ping", aliases=["latency", "latencia"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def ping(self, ctx: commands.Context) -> None:
        try:
            metrics = await asyncio.wait_for(
                self._measure_latency(ctx),
                timeout=self.MEASUREMENT_TIMEOUT
            )
            
            embed = self._build_embed(metrics)
            await ctx.reply(embed=embed, mention_author=False)
            
            logger.info(
                f"Ping executado | User: {ctx.author.id} | "
                f"WS: {metrics.websocket}ms | RT: {metrics.roundtrip}ms"
            )
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout na medição de latência | "
                f"Guild: {ctx.guild.id if ctx.guild else 'DM'} | "
                f"User: {ctx.author.id}"
            )
            await self._send_error(ctx, "⏱️ Tempo esgotado ao medir a latência.")
            
        except discord.Forbidden:
            logger.error(f"Permissões insuficientes | Guild: {ctx.guild.id if ctx.guild else 'DM'}")
            
        except Exception as e:
            logger.error(
                f"Erro no comando ping | User: {ctx.author.id} | Error: {e}",
                exc_info=True
            )
            await self._send_error(ctx, "❌ Erro ao processar o comando.")
    
    async def _measure_latency(self, ctx: commands.Context) -> PingMetrics:
        websocket_latency = self._get_websocket_latency()
        roundtrip_latency = await self._measure_roundtrip(ctx)
        database_latency = await self._measure_database()
        shard_id = ctx.guild.shard_id if ctx.guild else None
        
        return PingMetrics(
            websocket=websocket_latency,
            roundtrip=roundtrip_latency,
            database=database_latency,
            shard_id=shard_id
        )
    
    def _get_websocket_latency(self) -> float:
        return round(self.bot.latency * 1000, 2)
    
    async def _measure_roundtrip(self, ctx: commands.Context) -> float:
        start = time.perf_counter()
        message = await ctx.send("🏓")
        end = time.perf_counter()
        
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        
        return round((end - start) * 1000, 2)
    
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
            logger.error(f"Erro ao medir latência do database: {e}")
            return None
    
    def _build_embed(self, metrics: PingMetrics) -> discord.Embed:
        level = metrics.primary_level
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=level.color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="📡 Websocket",
            value=f"`{metrics.websocket}ms` {metrics.websocket_level.emoji}",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Round-trip",
            value=f"`{metrics.roundtrip}ms` {metrics.roundtrip_level.emoji}",
            inline=True
        )
        
        if metrics.database is not None:
            embed.add_field(
                name="💾 Database",
                value=f"`{metrics.database}ms` {metrics.database_level.emoji}",
                inline=True
            )
        
        footer_text = f"Latência: {level.label}"
        if metrics.shard_id is not None:
            footer_text += f" • Shard: {metrics.shard_id}"
        
        embed.set_footer(text=footer_text)
        
        return embed
    
    async def _send_error(self, ctx: commands.Context, message: str) -> None:
        try:
            await ctx.reply(message, mention_author=False)
        except discord.HTTPException:
            pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
