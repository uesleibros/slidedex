import io
import time
import textwrap
import traceback
from contextlib import redirect_stdout
import discord
from discord.ext import commands
from __main__ import toolkit, pm
from PIL import Image
import aiohttp
import json
import asyncio

class Dev(commands.Cog):
	hidden = True
	
	def __init__(self, bot):
		self.bot = bot

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

	@commands.is_owner()
	@commands.command(name="upscale", aliases=["up"])
	async def upscale_command(self, ctx: commands.Context, scale: int = 2, enhance: str = "yes"):
		try:
			img_bytes = None
			
			if ctx.message.attachments:
				img_bytes = await ctx.message.attachments[0].read()
			
			if not img_bytes:
				return await ctx.send("Nenhuma imagem encontrada")
			
			if scale < 1 or scale > 8:
				return await ctx.send("A escala deve ser entre 1 e 8")
			
			img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
			bbox = img.getbbox()
			img = img.crop(bbox)
			
			new_size = (img.width * scale, img.height * scale)
			img_upscaled = img.resize(new_size, Image.Resampling.NEAREST)
			
			buffer = io.BytesIO()
			img_upscaled.save(buffer, format="PNG", optimize=True)
			buffer.seek(0)
			
			file_size_mb = buffer.getbuffer().nbytes / (1024 * 1024)
			if file_size_mb > 24:
				buffer = io.BytesIO()
				img_upscaled.save(buffer, format="PNG", optimize=True, compress_level=9)
				buffer.seek(0)
				file_size_mb = buffer.getbuffer().nbytes / (1024 * 1024)
			
			file = discord.File(buffer, filename=f"upscaled_{scale}x.png")
			
			await ctx.send(file=file)
			
		except Exception as e:
			error_trace = traceback.format_exc()
			embed = discord.Embed(title="Erro ao processar imagem", description=f"```py\n{error_trace[:4000]}\n```", color=discord.Color.red())
			await ctx.send(embed=embed)

	async def process_item(self, ctx, item_id, session):
		try:
			url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{item_id}.png"
			
			async with session.get(url) as resp:
				if resp.status != 200:
					await ctx.send(f"Item `{item_id}` não encontrado")
					return None
				
				img_bytes = await resp.read()
			
			img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
			bbox = img.getbbox()
			if bbox:
				img = img.crop(bbox)
			
			scale = 8
			new_size = (img.width * scale, img.height * scale)
			img_upscaled = img.resize(new_size, Image.Resampling.NEAREST)
			
			buffer = io.BytesIO()
			img_upscaled.save(buffer, format="PNG", optimize=True)
			buffer.seek(0)
			
			file_size_mb = buffer.getbuffer().nbytes / (1024 * 1024)
			if file_size_mb > 24:
				buffer = io.BytesIO()
				img_upscaled.save(buffer, format="PNG", optimize=True, compress_level=9)
				buffer.seek(0)
			
			emoji_name = item_id.replace("-", "").replace("_", "")
			
			buffer.seek(0)
			emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=buffer.read())
			
			return {item_id: f"<:{emoji.name}:{emoji.id}>"}
		except Exception as e:
			await ctx.send(f"Erro ao processar `{item_id}`: {str(e)}")
			return None

	@commands.is_owner()
	@commands.command(name="addemoji", aliases=["ae"])
	async def add_emoji_command(self, ctx: commands.Context, item_id: str):
		try:
			async with aiohttp.ClientSession() as session:
				result = await self.process_item(ctx, item_id.replace(',', ''), session)
			
			if result:
				json_output = json.dumps(result, indent="\t", ensure_ascii=False)
				await ctx.send(f"```json\n{json_output}\n```")
			
		except Exception as e:
			error_trace = traceback.format_exc()
			embed = discord.Embed(title="Erro ao processar emojis", description=f"```py\n{error_trace[:4000]}\n```", color=discord.Color.red())
			await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
	await bot.add_cog(Dev(bot))