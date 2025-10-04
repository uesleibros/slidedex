import io
import time
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord.ext import commands
from __main__ import toolkit, pm

class Dev(commands.Cog):
    """ Comandos apenas para desenvolvedores. """
    def __init__(self, bot):
        self.bot = bot
        hidden = True

    def cleanup_code(self, content: str) -> str:
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip()

    def to_file(self, name: str, text: str) -> discord.File:
        fp = io.BytesIO(text.encode("utf-8"))
        return discord.File(fp, filename=name)

    @commands.is_owner()
    @commands.command(name="eval", aliases=["ev"])
    async def eval_command(self, ctx: commands.Context, *, body: str):
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "discord": discord,
            "commands": commands,
            "toolkit": toolkit,
            "pm": pm,
        }
        env.update(globals())
        code_input = self.cleanup_code(body)
        stdout = io.StringIO()
        is_expr = False
        try:
            code_obj = compile(code_input, "<eval>", "eval")
            is_expr = True
        except SyntaxError:
            code_obj = None
        start = time.perf_counter()
        try:
            with redirect_stdout(stdout):
                if is_expr:
                    try:
                        result = eval(code_obj, env)
                    except NameError:
                        result = code_input
                else:
                    exec(f"async def __eval_fn__():\n{textwrap.indent(code_input, '    ')}", env)
                    result = await env["__eval_fn__"]()
        except Exception:
            result = code_input
        elapsed = (time.perf_counter() - start) * 1000
        out = stdout.getvalue()
        if result is None:
            output = out if out else "None"
        else:
            output = f"{out}{result}" if out else f"{result}"
        text = f"{output}\n# {elapsed:.2f} ms"
        if len(text) > 1900:
            await ctx.send(file=self.to_file("eval_output.txt", text), allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send(f"```py\n{text}\n```", allowed_mentions=discord.AllowedMentions.none())
        try:
            del result
        except Exception:
            pass
        try:
            del out
        except Exception:
            pass
        try:
            del output
        except Exception:
            pass
        try:
            del text
        except Exception:
            pass
        try:
            del code_obj
        except Exception:
            pass
        try:
            del env
        except Exception:
            pass
        try:
            stdout.close()
            del stdout
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Dev(bot))

