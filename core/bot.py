import discord
import os
from pathlib import Path
from typing import Optional
from discord.ext import commands
from core.config import Config
from core.events import EventHandler
from core.errors import ErrorHandler
from core.help import CustomHelpCommand
from utilities.pokemon_emojis import load_application_emojis
from utilities.preloaded import preload_backgrounds, preload_info_backgrounds, preload_textures, preload_textures_arena

class PokemonBot(commands.Bot):
	def __init__(self, config: Config):
		intents = discord.Intents.default()
		intents.message_content = True
		intents.members = True
		
		super().__init__(
			command_prefix=config.prefix,
			intents=intents,
			help_command=CustomHelpCommand()
		)
		
		self.config = config
		self.event_handler = EventHandler(self)
		self.error_handler = ErrorHandler(self)
	
	async def setup_hook(self) -> None:
		await self._load_extensions()
		await self._preload_resources()
	
	async def on_ready(self) -> None:
		await self.event_handler.on_ready()
		await self._set_activity()
	
	async def on_message(self, message: discord.Message) -> None:
		await self.event_handler.on_message(message)
	
	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
		await self.error_handler.on_command_error(ctx, error)

	async def _set_activity(self) -> None:
		activity = discord.Activity(
			type=discord.ActivityType.playing,
			name="SlideDex v2.0 - Em Rewrite"
		)
		await self.change_presence(activity=activity, status=discord.Status.online)
	
	async def _load_extensions(self) -> None:
		cogs_path = Path("./cogs")
		loaded = set()
		
		for path in cogs_path.rglob("*.py"):
			module = self._get_module_name(path)
			
			if module and module not in loaded:
				await self._load_extension(module)
				loaded.add(module)
	
	def _get_module_name(self, path: Path) -> Optional[str]:
		if path.stem == "__init__":
			try:
				rel_path = path.parent.relative_to(Path("./cogs"))
				module = f"cogs.{rel_path.as_posix().replace('/', '.')}"
				return module if module != "cogs" else None
			except ValueError:
				return None
		
		if (path.parent / "__init__.py").exists():
			return None
		
		try:
			rel_path = path.relative_to(Path("./cogs")).with_suffix("")
			module = f"cogs.{rel_path.as_posix().replace('/', '.')}"
			return module
		except ValueError:
			return None
	
	async def _load_extension(self, module: str) -> None:
		try:
			await self.load_extension(module)
			print(f"Extensão carregada: {module}")
		except Exception as e:
			print(f"Falha ao carregar {module}: {e}")
	
	async def _preload_resources(self) -> None:
		await load_application_emojis(self)
		preload_backgrounds()
		preload_info_backgrounds()
		preload_textures()
		preload_textures_arena()