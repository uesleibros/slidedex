from discord.ext import commands
from typing import Optional
from helpers.custom_messages import CustomMessageSystem, MessageEvent, MessageContextBuilder
from helpers.checks import requires_account
from __main__ import pm
import math

class CustomMessages(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.message_system = CustomMessageSystem(pm.tk)

	@commands.group(name="messages", aliases=["msg", "custommsg"], invoke_without_command=True)
	@requires_account()
	async def messages_root(self, ctx: commands.Context):
		uid = str(ctx.author.id)
		messages = self.message_system.list_user_messages(uid)
		
		if not messages:
			return await ctx.send(
				"Você não tem mensagens customizadas.\n"
				"Use `.messages set <evento> <mensagem>` para criar!\n"
				"-# Use `.messages help` para ver exemplos."
			)
		
		lines = []
		for event_name, template in list(messages.items())[:10]:
			display_name = event_name.replace("_", "-")
			truncated = template[:100] + "..." if len(template) > 100 else template
			lines.append(f"**{display_name}**\n`{truncated}`")
		
		total = len(messages)
		footer = f"\n-# Total: {total} mensagem(ns)" + (f" | Mostrando 10 de {total}" if total > 10 else "")
		
		await ctx.send(
			f"📝 **Mensagens Customizadas de {ctx.author.name}:**\n\n" + 
			"\n\n".join(lines) + 
			footer
		)

	@messages_root.command(name="set")
	@requires_account()
	async def messages_set(self, ctx: commands.Context, event: Optional[str] = None, *, message: Optional[str] = None):
		uid = str(ctx.author.id)
		
		if not event or not message:
			return await ctx.send(
				"Uso: `.messages set <evento> <mensagem>`\n"
				"Exemplo: `.messages set capture [is_shiny]✨ [/is_shiny]{pokemon_name} capturado!`\n"
				"-# Use `.messages events` para ver eventos disponíveis.\n"
				"-# Use `.messages help` para aprender a usar variáveis."
			)
		
		try:
			event_enum = MessageEvent[event.upper().replace("-", "_")]
		except KeyError:
			events_sample = ", ".join([e.value.replace("_", "-") for e in list(MessageEvent)[:5]])
			return await ctx.send(
				f"❌ Evento `{event}` não existe!\n"
				f"Eventos disponíveis: {events_sample}...\n"
				"-# Use `.messages events` para ver todos."
			)
		
		if len(message) > 1000:
			return await ctx.send("❌ Mensagem muito longa! Máximo de 1000 caracteres.")
		
		self.message_system.set_message(uid, event_enum, message)
		
		example_context = self._create_example_context(event_enum)
		preview = self.message_system.preview_message(message, example_context)
		
		variables = CustomMessageSystem.get_context_variables(event_enum)
		vars_display = ", ".join(f"`{{{v}}}`" for v in variables[:8])
		
		await ctx.send(
			f"✅ **Mensagem salva para `{event_enum.value.replace('_', '-')}`**\n\n"
			f"**Preview:** {preview[:300]}\n\n"
			f"**Variáveis disponíveis:** {vars_display}{'...' if len(variables) > 8 else ''}\n"
			"-# Use `.messages preview` para testar antes de salvar."
		)

	@messages_root.command(name="preview")
	@requires_account()
	async def messages_preview(self, ctx: commands.Context, event: Optional[str] = None, *, message: Optional[str] = None):
		if not event or not message:
			return await ctx.send(
				"Uso: `.messages preview <evento> <mensagem>`\n"
				"Exemplo: `.messages preview capture {pokemon_name} foi capturado[is_shiny] ✨[/is_shiny]!`\n"
				"-# Testa como a mensagem vai aparecer."
			)
		
		try:
			event_enum = MessageEvent[event.upper().replace("-", "_")]
		except KeyError:
			return await ctx.send(f"❌ Evento `{event}` não existe! Use `.messages events` para ver todos.")
		
		example_context = self._create_example_context(event_enum)
		result = self.message_system.preview_message(message, example_context)
		
		await ctx.send(
			f"🔍 **Preview - `{event_enum.value.replace('_', '-')}`**\n\n"
			f"**Template:**\n```{message[:400]}```\n"
			f"**Resultado:**\n{result[:500]}\n"
			"-# Exemplo com valores fictícios."
		)

	@messages_root.command(name="reset")
	@requires_account()
	async def messages_reset(self, ctx: commands.Context, event: Optional[str] = None):
		uid = str(ctx.author.id)
		
		if not event:
			return await ctx.send(
				"Uso: `.messages reset <evento>`\n"
				"Exemplo: `.messages reset capture`\n"
				"-# Volta a mensagem para o padrão do bot."
			)
		
		try:
			event_enum = MessageEvent[event.upper().replace("-", "_")]
		except KeyError:
			return await ctx.send(f"❌ Evento `{event}` não existe!")
		
		success = self.message_system.reset_message(uid, event_enum)
		
		if success:
			default = CustomMessageSystem.DEFAULT_MESSAGES.get(event_enum, "")
			await ctx.send(
				f"✅ **Mensagem resetada para `{event_enum.value.replace('_', '-')}`**\n\n"
				f"**Padrão:** {default}"
			)
		else:
			await ctx.send(f"❌ Você não tinha uma mensagem customizada para `{event}`.")

	@messages_root.command(name="reset-all", aliases=["resetall", "clear"])
	@requires_account()
	async def messages_reset_all(self, ctx: commands.Context, confirm: Optional[str] = None):
		uid = str(ctx.author.id)
		
		messages = self.message_system.list_user_messages(uid)
		
		if not messages:
			return await ctx.send("Você não tem mensagens customizadas para resetar.")
		
		if confirm != "CONFIRMAR":
			total = len(messages)
			return await ctx.send(
				f"⚠️ **ATENÇÃO!** Isso vai deletar **{total} mensagem(ns) customizada(s)**!\n"
				"Esta ação não pode ser desfeita.\n\n"
				"Para confirmar, use: `.messages reset-all CONFIRMAR`"
			)
		
		success = self.message_system.reset_all_messages(uid)
		
		if success:
			await ctx.send("✅ **Todas as suas mensagens foram resetadas para o padrão.**")
		else:
			await ctx.send("❌ Erro ao resetar mensagens.")

	@messages_root.command(name="events", aliases=["list-events", "ev"])
	@requires_account()
	async def messages_events(self, ctx: commands.Context, page: int = 1):
		categories = {
			"⚔️ Batalha": [
				MessageEvent.BATTLE_WIN, MessageEvent.BATTLE_LOSS,
				MessageEvent.CRITICAL_HIT, MessageEvent.SUPER_EFFECTIVE,
				MessageEvent.NOT_VERY_EFFECTIVE, MessageEvent.MOVE_MISS,
				MessageEvent.MULTI_HIT, MessageEvent.ONE_HIT_KO,
				MessageEvent.TRAINER_BATTLE_START, MessageEvent.GYM_BATTLE_START,
				MessageEvent.RIVAL_BATTLE_START
			],
			"📦 Captura": [
				MessageEvent.CAPTURE, MessageEvent.CATCH_FAIL,
				MessageEvent.CATCH_CRITICAL, MessageEvent.PARTY_FULL
			],
			"✨ Encontros": [
				MessageEvent.SHINY_ENCOUNTER, MessageEvent.LEGENDARY_ENCOUNTER,
				MessageEvent.MYTHICAL_ENCOUNTER
			],
			"📈 Progresso": [
				MessageEvent.LEVEL_UP, MessageEvent.EVOLUTION,
				MessageEvent.LEARNED_MOVE, MessageEvent.FORGOT_MOVE
			],
			"💖 Status": [
				MessageEvent.POKEMON_FAINT, MessageEvent.STATUS_APPLIED,
				MessageEvent.PARALYZED_CANT_MOVE, MessageEvent.CONFUSED_HURT_ITSELF,
				MessageEvent.LOW_HP, MessageEvent.HAPPINESS_MAX,
				MessageEvent.MAX_HAPPINESS
			],
			"🎲 Outros": [
				MessageEvent.STAT_BOOST, MessageEvent.STAT_DROP,
				MessageEvent.HEALING, MessageEvent.RECOIL_DAMAGE,
				MessageEvent.WEATHER_DAMAGE, MessageEvent.IV_PERFECT,
				MessageEvent.RARE_ABILITY, MessageEvent.DODGE
			]
		}
		
		pages = []
		for category, events in categories.items():
			lines = [f"**{category}**\n"]
			for event in events:
				event_name = event.value.replace("_", "-")
				default_msg = CustomMessageSystem.DEFAULT_MESSAGES.get(event, "")
				truncated = default_msg[:60] + "..." if len(default_msg) > 60 else default_msg
				lines.append(f"`{event_name}`\n{truncated}")
			pages.append("\n\n".join(lines))
		
		total_pages = len(pages)
		page = max(1, min(page, total_pages))
		
		await ctx.send(
			f"📋 **Eventos Disponíveis** (Página {page}/{total_pages})\n\n"
			f"{pages[page-1]}\n\n"
			f"-# Use `.messages events <número>` para ver outras páginas.\n"
			f"-# Use `.messages set <evento> <mensagem>` para customizar."
		)

	@messages_root.command(name="help", aliases=["guide", "h"])
	@requires_account()
	async def messages_help(self, ctx: commands.Context, topic: Optional[str] = None):
		if not topic:
			return await ctx.send(
				"📚 **Guia de Mensagens Customizadas**\n\n"
				"**Comandos:**\n"
				"`.messages set <evento> <mensagem>` - Define mensagem\n"
				"`.messages preview <evento> <mensagem>` - Testa mensagem\n"
				"`.messages reset <evento>` - Reseta para padrão\n"
				"`.messages events` - Ver todos eventos\n"
				"`.messages` - Ver suas mensagens\n\n"
				"**Tópicos de Ajuda:**\n"
				"`.messages help variables` - Como usar variáveis\n"
				"`.messages help conditionals` - Como usar condicionais\n"
				"`.messages help examples` - Ver exemplos práticos\n"
				"`.messages help operators` - Lista de operadores\n"
			)
		
		topic = topic.lower()
		
		if topic in ["variables", "var", "v"]:
			await ctx.send(
				"🔤 **Usando Variáveis**\n\n"
				"Use `{nome_variavel}` para inserir valores dinâmicos.\n\n"
				"**Exemplos:**\n"
				"`{pokemon_name}` → Nome do Pokémon\n"
				"`{level}` → Nível atual\n"
				"`{is_shiny}` → Se é shiny (sim/não)\n"
				"`{iv_percent}` → Porcentagem de IV\n"
				"`{types}` → Tipos do Pokémon\n"
				"`{happiness}` → Felicidade (0-255)\n\n"
				"**Uso:**\n"
				"```{pokemon_name} subiu para o nível {level}!```\n"
				"**Resultado:**\n"
				"Pikachu subiu para o nível 50!\n\n"
				"-# Cada evento tem variáveis específicas disponíveis."
			)
		
		elif topic in ["conditionals", "cond", "c"]:
			await ctx.send(
				"🔀 **Usando Condicionais**\n\n"
				"Mostra texto apenas se uma condição for verdadeira.\n\n"
				"**Sintaxe:**\n"
				"`[condicao]texto[/condicao]`\n\n"
				"**Exemplos:**\n"
				"`[is_shiny]✨ SHINY! ✨[/is_shiny]`\n"
				"Mostra apenas se for shiny\n\n"
				"`[level>=50]Muito forte![/level>=50]`\n"
				"Mostra apenas se nível >= 50\n\n"
				"`[iv_percent>90]IVs incríveis![/iv_percent>90]`\n"
				"Mostra apenas se IV > 90%\n\n"
				"`[type contains fire]🔥[/type contains fire]`\n"
				"Mostra apenas se tem tipo fogo\n\n"
				"-# Use `.messages help operators` para ver todos operadores."
			)
		
		elif topic in ["operators", "op", "o"]:
			await ctx.send(
				"⚙️ **Operadores Disponíveis**\n\n"
				"`=` → Igual\n"
				"`!=` → Diferente\n"
				"`>` → Maior que\n"
				"`<` → Menor que\n"
				"`>=` → Maior ou igual\n"
				"`<=` → Menor ou igual\n"
				"`contains` → Contém\n"
				"`in` → Está em\n\n"
				"**Exemplos:**\n"
				"`[level=100]NÍVEL MÁXIMO![/level=100]`\n"
				"`[level!=1]Não é iniciante[/level!=1]`\n"
				"`[happiness>=200]Muito feliz![/happiness>=200]`\n"
				"`[type contains dragon]🐉[/type contains dragon]`\n"
			)
		
		elif topic in ["examples", "ex", "e"]:
			await ctx.send(
				"💡 **Exemplos Práticos**\n\n"
				"**Captura Épica:**\n"
				"```[is_shiny]✨ [/is_shiny]{pokemon_name} capturado"
				"[critical_capture] (captura crítica!)[/critical_capture]"
				"[iv_percent>=95] com IVs PERFEITOS[/iv_percent>=95]!```\n\n"
				"**Level Up Progressivo:**\n"
				"```{pokemon_name} subiu para nível {new_level}"
				"[new_level<30]![/new_level<30]"
				"[new_level>=30][new_level<70]! Está ficando forte![/new_level<70][/new_level>=30]"
				"[new_level>=70]! MUITO PODEROSO![/new_level>=70]```\n\n"
				"**Evolução Shiny:**\n"
				"```🎉 {old_name} → {new_name}! 🎉"
				"[is_shiny]\n✨ E CONTINUA SHINY! ✨[/is_shiny]```\n\n"
				"-# Combine variáveis e condicionais para mensagens únicas!"
			)
		
		else:
			await ctx.send(
				f"❌ Tópico `{topic}` não encontrado.\n"
				"Tópicos: `variables`, `conditionals`, `operators`, `examples`"
			)

	@messages_root.command(name="variables", aliases=["vars"])
	@requires_account()
	async def messages_variables(self, ctx: commands.Context, event: Optional[str] = None):
		if not event:
			return await ctx.send(
				"Uso: `.messages variables <evento>`\n"
				"Exemplo: `.messages variables capture`\n"
				"-# Mostra todas as variáveis disponíveis para um evento."
			)
		
		try:
			event_enum = MessageEvent[event.upper().replace("-", "_")]
		except KeyError:
			return await ctx.send(f"❌ Evento `{event}` não existe!")
		
		variables = CustomMessageSystem.get_context_variables(event_enum)
		example_context = self._create_example_context(event_enum)
		
		lines = []
		for var in variables[:15]:
			value = example_context.get(var, "N/A")
			if isinstance(value, bool):
				value = "sim" if value else "não"
			elif isinstance(value, list):
				value = ", ".join(str(v) for v in value)
			elif isinstance(value, float):
				value = f"{value:.2f}"
			lines.append(f"`{{{var}}}` → {value}")
		
		total = len(variables)
		footer = f"\n-# Total: {total} variável(is)" + (f" | Mostrando 15 de {total}" if total > 15 else "")
		
		await ctx.send(
			f"🔤 **Variáveis para `{event_enum.value.replace('_', '-')}`**\n\n" +
			"\n".join(lines) +
			footer
		)

	def _create_example_context(self, event: MessageEvent):
		base_context = {
			"pokemon_name": "Pikachu",
			"level": 50,
			"is_shiny": True,
			"is_legendary": False,
			"is_mythical": False,
			"types": ["electric"],
			"nature": "Jolly",
			"ability": "Static",
			"gender": "Male",
			"iv_percent": 95.5,
			"iv_total": 178,
			"happiness": 255,
			"current_hp": 120,
			"max_hp": 150,
			"hp_percent": 80.0
		}
		
		specific_contexts = {
			MessageEvent.CAPTURE: {
				"ball_type": "Ultra Ball",
				"critical_capture": True,
				"already_caught": False,
				"shake_count": 4
			},
			MessageEvent.EVOLUTION: {
				"old_name": "Pichu",
				"new_name": "Pikachu",
				"evolution_method": "friendship",
				"old_level": 15
			},
			MessageEvent.LEVEL_UP: {
				"old_level": 49,
				"new_level": 50,
				"exp_gained": 1500
			},
			MessageEvent.BATTLE_WIN: {
				"exp_gained": 2000,
				"money_gained": 1500,
				"turns": 15
			},
			MessageEvent.CRITICAL_HIT: {
				"move_name": "Thunderbolt",
				"damage": 85,
				"target_name": "Charizard"
			},
			MessageEvent.SUPER_EFFECTIVE: {
				"move_name": "Thunderbolt",
				"effectiveness": 2.0,
				"target_name": "Gyarados"
			},
			MessageEvent.STAT_BOOST: {
				"stat": "Attack",
				"stages": 2
			},
			MessageEvent.HEALING: {
				"hp_recovered": 50
			},
			MessageEvent.MULTI_HIT: {
				"hits": 5,
				"move_name": "Fury Attack",
				"total_damage": 125
			},
			MessageEvent.LEARNED_MOVE: {
				"move_name": "Thunderbolt",
				"move_type": "electric",
				"move_power": 90
			}
		}
		
		base_context.update(specific_contexts.get(event, {}))
		return base_context


async def setup(bot: commands.Bot):
	await bot.add_cog(CustomMessages(bot))
