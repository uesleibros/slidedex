import io
import time
import textwrap
import traceback
import sys
from contextlib import redirect_stdout, suppress
import discord
from discord.ext import commands
from PIL import Image
from sdk.toolkit import Toolkit

class Dev(commands.Cog):
    hidden = True
    
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def cleanup_code(content: str) -> str:
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip()

    @commands.is_owner()
    @commands.command(name="eval", aliases=["ev"])
    async def eval_command(self, ctx: commands.Context, *, body: str):
        code_input = self.cleanup_code(body)
        
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "discord": discord,
            "commands": commands,
            "tk": Toolkit(),
            **globals()
        }
        
        stdout = io.StringIO()
        start = time.perf_counter()
        result = None
        error = None
        
        try:
            with redirect_stdout(stdout):
                try:
                    result = eval(compile(code_input, "<eval>", "eval"), env)
                except SyntaxError:
                    exec(f"async def __ex():\n{textwrap.indent(code_input, '  ')}", env)
                    result = await env["__ex"]()
        except Exception as e:
            error = e
            tb = traceback.extract_tb(e.__traceback__)
            
            relevant_tb = None
            for frame in reversed(tb):
                if frame.filename in ("<eval>", "<string>"):
                    relevant_tb = frame
                    break
            
            error_msg = f"{type(e).__name__}: {e}"
            
            elapsed = (time.perf_counter() - start) * 1000
            await ctx.send(f"```py\n{error_msg}\n# {elapsed:.2f} ms\n```", allowed_mentions=discord.AllowedMentions.none())
            return
        finally:
            env.clear()
        
        elapsed = (time.perf_counter() - start) * 1000
        
        out = stdout.getvalue()
        stdout.close()
        
        if result is not None:
            output = f"{out}{result}" if out else str(result)
        else:
            output = out if out else "None"
        
        text = f"{output}\n# {elapsed:.2f} ms"
        
        if len(text) > 1900:
            fp = io.BytesIO(text.encode("utf-8"))
            await ctx.send(file=discord.File(fp, "eval.txt"), allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send(f"```py\n{text}\n```", allowed_mentions=discord.AllowedMentions.none())

    @commands.is_owner()
    @commands.command(name="upscale", aliases=["up"])
    async def upscale_command(self, ctx: commands.Context, scale: int = 2):
        if not ctx.message.attachments:
            return await ctx.send("Nenhuma imagem anexada")
        
        if not 1 <= scale <= 8:
            return await ctx.send("Escala deve ser entre 1 e 8")
        
        try:
            img_bytes = await ctx.message.attachments[0].read()
            
            with Image.open(io.BytesIO(img_bytes)).convert("RGBA") as img:
                img = img.crop(img.getbbox())
                new_size = (img.width * scale, img.height * scale)
                img_upscaled = img.resize(new_size, Image.Resampling.NEAREST)
                
                buffer = io.BytesIO()
                img_upscaled.save(buffer, format="PNG", optimize=True)
                buffer.seek(0)
                
                if buffer.getbuffer().nbytes > 25_165_824:
                    buffer = io.BytesIO()
                    img_upscaled.save(buffer, format="PNG", optimize=True, compress_level=9)
                    buffer.seek(0)
                
                await ctx.send(file=discord.File(buffer, f"upscaled_{scale}x.png"))
        
        except Exception as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")

async def setup(bot: commands.Bot):
    await bot.add_cog(Dev(bot))


