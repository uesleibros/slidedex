import os
import discord
from typing import Optional
from discord.ext import commands
from discord.ext.flags import ArgumentParsingError
from dotenv import load_dotenv
from utils.pokemon_emojis import load_application_emojis
from utils.preloaded import preload_backgrounds, preload_info_backgrounds, preload_textures

load_dotenv()
TOKEN: Optional[str] = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
	await load_application_emojis(bot)

	for root, _, files in os.walk("./cogs"):
		for filename in files:
			if filename.endswith(".py"):
				rel_path = os.path.relpath(os.path.join(root, filename), "./cogs")
				module = "cogs." + rel_path.replace(os.sep, ".")[:-3]
				
				if filename == "__init__.py":
					module = module.rsplit(".", 1)[0]
					
					if module == "cogs":
						continue
					
					await bot.load_extension(module)
					print(f"📂 Cog carregada: {module}")
				elif "__init__.py" not in files:
					await bot.load_extension(module)
					print(f"📂 Cog carregada: {module}")

	preload_backgrounds()
	preload_info_backgrounds()
	preload_textures()
	print(f"{bot.user} online")

@bot.event
async def on_message(message: discord.Message):
	if message.author.bot:
		return
	
	if bot.user.mentioned_in(message) and not message.mention_everyone:
		if message.content.strip() in [f'<@{bot.user.id}>', f'<@!{bot.user.id}>']:
			await message.channel.send(f"Olá {message.author.mention}! Meu prefixo é `{bot.command_prefix}`\nUse `{bot.command_prefix}help` para ver todos os comandos!")
	
	await bot.process_commands(message)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
	if isinstance(error, ArgumentParsingError):
		await ctx.send(f"Erro nos argumentos: {str(error)}\n-# Use `.help {ctx.command.qualified_name}` para ver o uso correto.")
		return
	
	if isinstance(error, commands.CommandNotFound):
		return
	
	if isinstance(error, commands.MissingRequiredArgument):
		await ctx.send(f"Argumento obrigatório faltando: `{error.param.name}`\n-# Use `.help {ctx.command.qualified_name}` para ver o uso correto.")
		return
	
	if isinstance(error, commands.BadArgument):
		await ctx.send(f"Argumento inválido: {str(error)}")
		return
	
	if isinstance(error, commands.CommandOnCooldown):
		await ctx.send(f"Calma! Tente novamente em **{error.retry_after:.1f}s**")
		return
	
	if isinstance(error, commands.MissingPermissions):
		await ctx.send(f"Você não tem permissão para usar este comando!")
		return
	
	if isinstance(error, commands.BotMissingPermissions):
		await ctx.send(f"Eu não tenho permissão para executar este comando!")
		return
	
	if isinstance(error, commands.CheckFailure):
		await ctx.send(f"Você não pode usar este comando agora.")
		return
	
	raise error

class HelpPaginator(discord.ui.View):
	def __init__(self, embeds, author):
		super().__init__(timeout=180)
		self.embeds = embeds
		self.author = author
		self.current = 0
		self.update_buttons()

	def update_buttons(self):
		self.previous.disabled = self.current == 0
		self.next.disabled = self.current == len(self.embeds) - 1

	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray)
	async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.author.id:
			return await interaction.response.send_message("Você não pode usar isso!", ephemeral=True)
		self.current -= 1
		self.update_buttons()
		await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray)
	async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.author.id:
			return await interaction.response.send_message("Você não pode usar isso!", ephemeral=True)
		self.current += 1
		self.update_buttons()
		await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

class MyHelpCommand(commands.HelpCommand):
	def get_command_signature(self, command):
		try:
			return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'
		except AttributeError:
			return f'{self.context.clean_prefix}{command.qualified_name}'

	async def send_bot_help(self, mapping):
		embeds = []
		categories = {}
		
		for cog, cmds in mapping.items():
			if cmds:
				if cog and getattr(cog, 'hidden', False):
					continue
				cog_name = cog.qualified_name if cog else "Sem Categoria"
				categories[cog_name] = [cmd for cmd in cmds if not cmd.hidden]
		
		items_per_page = 5
		cog_items = list(categories.items())
		total_pages = (len(cog_items) + items_per_page - 1) // items_per_page
		
		for page in range(total_pages):
			embed = discord.Embed(
				title=f"Categorias de Comandos (Página {page + 1}/{total_pages})",
				description=f"Use `{self.context.clean_prefix}help <comando>` para mais info.\nUse `{self.context.clean_prefix}help <categoria>` para mais info sobre uma categoria.",
				color=discord.Color.pink()
			)
			
			start = page * items_per_page
			end = start + items_per_page
			
			for cog_name, cmds in cog_items[start:end]:
				cog_obj = self.context.bot.get_cog(cog_name)
				description = cog_obj.description if cog_obj and cog_obj.description else "Sem descrição"
				commands_list = " ".join([cmd.name for cmd in cmds])
				embed.add_field(
					name=f"**{cog_name}**",
					value=f"{description}\n`{commands_list}`",
					inline=False
				)
			
			embeds.append(embed)
		
		if len(embeds) == 1:
			await self.get_destination().send(embed=embeds[0])
		else:
			view = HelpPaginator(embeds, self.context.author)
			await self.get_destination().send(embed=embeds[0], view=view)

	async def send_cog_help(self, cog):
		embed = discord.Embed(
			title=f"Categoria: {cog.qualified_name}",
			description=cog.description or "Sem descrição",
			color=discord.Color.pink()
		)
		
		commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
		if commands_list:
			embed.add_field(
				name="Comandos",
				value="\n".join([f"`{self.get_command_signature(cmd)}`\n{cmd.short_doc or 'Sem descrição'}" for cmd in commands_list]),
				inline=False
			)
		
		await self.get_destination().send(embed=embed)

	async def send_command_help(self, command):
		help_text = command.help or "Sem descrição"
		
		if len(help_text) > 4000:
			embeds = []
			chunks = []
			current_chunk = ""
			
			for line in help_text.split('\n'):
				if len(current_chunk) + len(line) + 1 > 4000:
					chunks.append(current_chunk)
					current_chunk = line + '\n'
				else:
					current_chunk += line + '\n'
			
			if current_chunk:
				chunks.append(current_chunk)
			
			for i, chunk in enumerate(chunks):
				embed = discord.Embed(
					title=f"{self.get_command_signature(command)} (Página {i+1}/{len(chunks)})",
					description=chunk,
					color=discord.Color.pink()
				)
				
				if i == 0 and command.aliases:
					embed.add_field(
						name="Aliases",
						value=", ".join([f"`{alias}`" for alias in command.aliases]),
						inline=False
					)
				
				embeds.append(embed)
			
			if len(embeds) == 1:
				await self.get_destination().send(embed=embeds[0])
			else:
				view = HelpPaginator(embeds, self.context.author)
				await self.get_destination().send(embed=embeds[0], view=view)
		else:
			embed = discord.Embed(
				title=self.get_command_signature(command),
				description=help_text,
				color=discord.Color.pink()
			)
			
			if command.aliases:
				embed.add_field(
					name="Aliases",
					value=", ".join([f"`{alias}`" for alias in command.aliases]),
					inline=False
				)
			
			await self.get_destination().send(embed=embed)

	async def send_group_help(self, group):
		embeds = []
		subcommands = [cmd for cmd in group.commands if not cmd.hidden]
		
		items_per_page = 5
		total_pages = (len(subcommands) + items_per_page - 1) // items_per_page if subcommands else 1
		
		for page in range(total_pages):
			help_text = group.help or "Sem descrição"
			
			if len(help_text) > 2000:
				help_text = help_text[:1997] + "..."
			
			embed = discord.Embed(
				title=self.get_command_signature(group),
				description=help_text,
				color=discord.Color.pink()
			)
			
			if group.aliases:
				embed.add_field(
					name="Aliases",
					value=", ".join([f"`{alias}`" for alias in group.aliases]),
					inline=False
				)
			
			if subcommands:
				start = page * items_per_page
				end = start + items_per_page
				page_subcommands = subcommands[start:end]
				
				subcommands_text = "\n".join([
					f"`{self.get_command_signature(cmd)}`\n{cmd.short_doc or 'Sem descrição'}"
					for cmd in page_subcommands
				])
				
				if len(subcommands_text) > 1000:
					subcommands_text = "\n".join([
						f"`{self.get_command_signature(cmd)}`"
						for cmd in page_subcommands
					])
				
				embed.add_field(
					name=f"Subcomandos (Página {page + 1}/{total_pages})",
					value=subcommands_text,
					inline=False
				)
			
			embeds.append(embed)
		
		if len(embeds) == 1:
			await self.get_destination().send(embed=embeds[0])
		else:
			view = HelpPaginator(embeds, self.context.author)
			await self.get_destination().send(embed=embeds[0], view=view)

bot.help_command = MyHelpCommand()
bot.run(str(TOKEN))