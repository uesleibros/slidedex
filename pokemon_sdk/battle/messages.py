from typing import Optional
from .constants import STAT_NAMES, STATUS_MESSAGES

class BattleMessages:
	
	@staticmethod
	def damage(attacker: str, move: str, damage: int, special: str = "") -> str:
		"""Mensagem de dano básica."""
		base = f"{attacker} usou **{move}**!"
		if damage > 0:
			base += f" ({damage} de dano)"
		if special:
			base += f" {special}"
		return base
	
	@staticmethod
	def status_applied(pokemon: str, status: str) -> str:
		"""Mensagem quando status é aplicado."""
		icons = {
			"burn": "🔥",
			"poison": "☠️",
			"paralysis": "⚡",
			"sleep": "💤",
			"freeze": "❄️",
			"toxic": "☠️☠️"
		}
		icon = icons.get(status, "💫")
		msg = STATUS_MESSAGES.get(status, "foi afetado")
		return f"   └─ {icon} {pokemon} {msg}!"
	
	@staticmethod
	def status_cured(pokemon: str, status: str) -> str:
		"""Mensagem quando status é curado."""
		status_names = {
			"burn": "queimadura",
			"poison": "envenenamento",
			"paralysis": "paralisia",
			"sleep": "sono",
			"freeze": "congelamento",
			"toxic": "envenenamento tóxico"
		}
		return f"   └─ ✨ {pokemon} se recuperou de {status_names.get(status, status)}!"
	
	@staticmethod
	def already_has_status(pokemon: str) -> str:
		"""Mensagem quando Pokémon já tem status."""
		return f"   └─ 💢 {pokemon} já tem um status!"
	
	@staticmethod
	def stat_change(pokemon: str, stat: str, stages: int) -> str:
		"""Mensagem de mudança de stat."""
		stat_name = STAT_NAMES.get(stat, stat)
		if stages > 0:
			arrows = "↑" * min(abs(stages), 3)
			if abs(stages) >= 3:
				level = "drasticamente"
			elif abs(stages) == 2:
				level = "muito"
			else:
				level = ""
			return f"   └─ 📈 {stat_name} de {pokemon} aumentou {level} {arrows}".strip()
		else:
			arrows = "↓" * min(abs(stages), 3)
			if abs(stages) >= 3:
				level = "drasticamente"
			elif abs(stages) == 2:
				level = "muito"
			else:
				level = ""
			return f"   └─ 📉 {stat_name} de {pokemon} diminuiu {level} {arrows}".strip()
	
	@staticmethod
	def stat_maxed(pokemon: str, stat: str, is_max: bool = True) -> str:
		"""Mensagem quando stat já está no limite."""
		stat_name = STAT_NAMES.get(stat, stat)
		limit = "máximo" if is_max else "mínimo"
		return f"   └─ 💢 {stat_name} de {pokemon} já está no {limit}!"
	
	@staticmethod
	def stats_reset(pokemon: str = None, all_pokemon: bool = False) -> str:
		"""Mensagem quando stats são resetados."""
		if all_pokemon:
			return "   └─ 🌫️ Todas as mudanças de stats foram resetadas!"
		return f"   └─ 🔄 Stats de {pokemon} foram resetados!"
	
	@staticmethod
	def healing(pokemon: str, amount: int) -> str:
		"""Mensagem de cura."""
		return f"   └─ 💚 {pokemon} recuperou {amount} HP!"
	
	@staticmethod
	def recoil(pokemon: str, amount: int) -> str:
		"""Mensagem de recuo."""
		return f"   └─ 💥 {pokemon} sofreu {amount} de recuo!"
	
	@staticmethod
	def drain(pokemon: str, amount: int) -> str:
		"""Mensagem de drenagem."""
		return f"   └─ 💉 {pokemon} drenou {amount} HP!"
	
	@staticmethod
	def fainted(pokemon: str) -> str:
		"""Mensagem de desmaio."""
		return f"💀 **{pokemon} foi derrotado!**"
	
	@staticmethod
	def miss(pokemon: str, move: str) -> str:
		"""Mensagem de erro."""
		return f"💨 {pokemon} usou **{move}**, mas errou!"
	
	@staticmethod
	def no_effect(pokemon: str, move: str) -> str:
		"""Mensagem quando não tem efeito."""
		return f"🚫 {pokemon} usou **{move}**!\n   └─ Não teve efeito!"
	
	@staticmethod
	def protected(pokemon: str) -> str:
		"""Mensagem de proteção."""
		return f"🛡️ {pokemon} se protegeu do ataque!"
	
	@staticmethod
	def immune(pokemon: str, reason: str = "") -> str:
		"""Mensagem de imunidade."""
		if reason:
			return f"   └─ 💢 {pokemon} é imune ({reason})!"
		return f"   └─ 💢 {pokemon} é imune!"
	
	@staticmethod
	def failed(move: str = None) -> str:
		"""Mensagem de falha."""
		if move:
			return f"   └─ 💢 **{move}** falhou!"
		return "   └─ 💢 Mas falhou!"
	
	@staticmethod
	def details(hits: Optional[int] = None, crit: bool = False, effectiveness: float = 1.0) -> Optional[str]:
		"""Mensagem de detalhes do ataque."""
		parts = []
		if hits and hits > 1:
			parts.append(f"🎯 {hits}x hits")
		if crit:
			parts.append("💥 CRÍTICO")
		if effectiveness > 1.0:
			parts.append("✨ Super eficaz")
		elif 0 < effectiveness < 1.0:
			parts.append("💢 Pouco eficaz")
		
		return "   └─ " + " • ".join(parts) if parts else None
	
	# ==================== VOLATILE EFFECTS ====================
	
	@staticmethod
	def confused(pokemon: str) -> str:
		"""Mensagem de confusão."""
		return f"   └─ 😵 {pokemon} ficou confuso!"
	
	@staticmethod
	def confusion_hurt(pokemon: str, damage: int) -> str:
		"""Mensagem quando se machuca na confusão."""
		return f"😵 {pokemon} está confuso e se machucou! ({damage} de dano)"
	
	@staticmethod
	def confusion_ended(pokemon: str) -> str:
		"""Mensagem quando confusão acaba."""
		return f"   └─ ✨ {pokemon} não está mais confuso!"
	
	@staticmethod
	def flinched(pokemon: str) -> str:
		"""Mensagem de flinch."""
		return f"😰 {pokemon} se encolheu e não conseguiu atacar!"
	
	@staticmethod
	def attracted(pokemon: str, target: str) -> str:
		"""Mensagem de atração."""
		return f"   └─ 💕 {pokemon} se apaixonou por {target}!"
	
	@staticmethod
	def immobilized_by_love(pokemon: str) -> str:
		"""Mensagem quando está apaixonado."""
		return f"💕 {pokemon} está apaixonado e não consegue atacar!"
	
	@staticmethod
	def seeded(pokemon: str) -> str:
		"""Mensagem de Leech Seed."""
		return f"   └─ 🌱 {pokemon} foi semeado!"
	
	@staticmethod
	def seed_sap(pokemon: str, damage: int, healer: str, heal: int) -> str:
		"""Mensagem de drenagem de Leech Seed."""
		return f"🌱 {pokemon} perdeu {damage} HP!\n   └─ {healer} recuperou {heal} HP!"
	
	@staticmethod
	def bound(pokemon: str, turns: int, move: str = "Bind") -> str:
		"""Mensagem de aprisionamento."""
		return f"   └─ 🎯 {pokemon} foi preso por {move}! ({turns} turnos)"
	
	@staticmethod
	def bound_damage(pokemon: str, damage: int, move: str = "Bind") -> str:
		"""Mensagem de dano de bind."""
		return f"🎯 {pokemon} sofreu {damage} de dano de {move}!"
	
	@staticmethod
	def freed_from_bind(pokemon: str) -> str:
		"""Mensagem quando se liberta."""
		return f"   └─ ✨ {pokemon} se libertou!"
	
	@staticmethod
	def trapped(pokemon: str) -> str:
		"""Mensagem de armadilha."""
		return f"   └─ 🕸️ {pokemon} não pode fugir!"
	
	@staticmethod
	def substitute_made(pokemon: str, hp_cost: int) -> str:
		"""Mensagem de substitute."""
		return f"   └─ 🎭 {pokemon} criou um substituto! (-{hp_cost} HP)"
	
	@staticmethod
	def substitute_faded(pokemon: str) -> str:
		"""Mensagem quando substitute quebra."""
		return f"   └─ 💔 O substituto de {pokemon} desapareceu!"
	
	@staticmethod
	def substitute_took_hit(pokemon: str) -> str:
		"""Mensagem quando substitute toma hit."""
		return f"   └─ 🎭 O substituto de {pokemon} tomou o golpe!"
	
	# ==================== WEATHER ====================
	
	@staticmethod
	def weather_started(weather: str, turns: int = 5) -> str:
		"""Mensagem de início de clima."""
		weather_msgs = {
			"sun": "☀️ O sol está forte!",
			"rain": "🌧️ Começou a chover!",
			"hail": "❄️ Começou a gear!",
			"sandstorm": "🌪️ Uma tempestade de areia começou!"
		}
		return f"   └─ {weather_msgs.get(weather, '🌤️ O clima mudou!')}"
	
	@staticmethod
	def weather_continues(weather: str) -> str:
		"""Mensagem de clima contínuo."""
		weather_msgs = {
			"sun": "☀️ O sol continua forte!",
			"rain": "🌧️ A chuva continua!",
			"hail": "❄️ O granizo continua!",
			"sandstorm": "🌪️ A tempestade continua!"
		}
		return weather_msgs.get(weather, "🌤️ O clima continua!")
	
	@staticmethod
	def weather_ended(weather: str = None) -> str:
		"""Mensagem de fim de clima."""
		return "🌤️ O clima voltou ao normal!"
	
	@staticmethod
	def weather_damage(pokemon: str, damage: int, weather: str) -> str:
		"""Mensagem de dano de clima."""
		weather_icons = {
			"hail": "❄️",
			"sandstorm": "🌪️"
		}
		icon = weather_icons.get(weather, "🌤️")
		return f"{icon} {pokemon} sofreu {damage} de dano do {weather}!"
	
	# ==================== FIELD EFFECTS ====================
	
	@staticmethod
	def spikes_set(layers: int) -> str:
		"""Mensagem de spikes."""
		return f"   └─ ⚠️ Spikes foram espalhados! (Nível {layers})"
	
	@staticmethod
	def spikes_damage(pokemon: str, damage: int) -> str:
		"""Mensagem de dano de spikes."""
		return f"⚠️ {pokemon} foi ferido por Spikes! ({damage} de dano)"
	
	@staticmethod
	def toxic_spikes_set(layers: int) -> str:
		"""Mensagem de toxic spikes."""
		return f"   └─ ☠️ Toxic Spikes foram espalhados! (Nível {layers})"
	
	@staticmethod
	def stealth_rock_set() -> str:
		"""Mensagem de stealth rock."""
		return "   └─ 🪨 Rochas pontiagudas flutuam ao redor!"
	
	@staticmethod
	def stealth_rock_damage(pokemon: str, damage: int) -> str:
		"""Mensagem de dano de stealth rock."""
		return f"🪨 {pokemon} foi ferido por rochas pontiagudas! ({damage} de dano)"
	
	@staticmethod
	def light_screen_set(turns: int = 5) -> str:
		"""Mensagem de Light Screen."""
		return f"   └─ ✨ Light Screen foi erguido! ({turns} turnos)"
	
	@staticmethod
	def reflect_set(turns: int = 5) -> str:
		"""Mensagem de Reflect."""
		return f"   └─ 🪞 Reflect foi erguido! ({turns} turnos)"
	
	@staticmethod
	def safeguard_set(turns: int = 5) -> str:
		"""Mensagem de Safeguard."""
		return f"   └─ 🛡️ Safeguard protege contra status! ({turns} turnos)"
	
	@staticmethod
	def mist_set(turns: int = 5) -> str:
		"""Mensagem de Mist."""
		return f"   └─ 🌫️ Uma névoa protetora se formou! ({turns} turnos)"
	
	@staticmethod
	def protected_by_mist(pokemon: str) -> str:
		"""Mensagem de proteção de Mist."""
		return f"   └─ 🌫️ A névoa protegeu {pokemon}!"
	
	@staticmethod
	def trick_room_set(turns: int = 5) -> str:
		"""Mensagem de Trick Room."""
		return f"   └─ 🔄 Trick Room distorceu as dimensões! ({turns} turnos)"
	
	@staticmethod
	def trick_room_ended() -> str:
		"""Mensagem de fim de Trick Room."""
		return "   └─ 🔄 Trick Room acabou!"
	
	@staticmethod
	def gravity_set(turns: int = 5) -> str:
		"""Mensagem de Gravity."""
		return f"   └─ ⬇️ Gravidade intensificada! ({turns} turnos)"
	
	@staticmethod
	def gravity_ended() -> str:
		"""Mensagem de fim de Gravity."""
		return "   └─ ⬇️ Gravidade voltou ao normal!"
	
	# ==================== SPECIAL MOVES ====================
	
	@staticmethod
	def transformed(user: str, target: str) -> str:
		"""Mensagem de Transform."""
		return f"   └─ 🔄 {user} se transformou em {target}!"
	
	@staticmethod
	def type_changed(pokemon: str, new_type: str) -> str:
		"""Mensagem de mudança de tipo."""
		return f"   └─ 🔀 {pokemon} mudou para o tipo {new_type.upper()}!"
	
	@staticmethod
	def ability_copied(user: str, ability: str, target: str = None) -> str:
		"""Mensagem de cópia de habilidade."""
		if target:
			return f"   └─ 🎭 {user} copiou {ability} de {target}!"
		return f"   └─ 🎭 {user} copiou {ability}!"
	
	@staticmethod
	def ability_swapped(user: str, user_ability: str, target: str, target_ability: str) -> str:
		"""Mensagem de troca de habilidade."""
		return f"   └─ 🔄 Habilidades trocadas! ({user_ability} ↔ {target_ability})"
	
	@staticmethod
	def item_stolen(user: str, item: str, target: str) -> str:
		"""Mensagem de roubo de item."""
		return f"   └─ 🎯 {user} roubou {item} de {target}!"
	
	@staticmethod
	def item_knocked_off(pokemon: str, item: str) -> str:
		"""Mensagem de item derrubado."""
		return f"   └─ 👊 {item} foi derrubado de {pokemon}!"
	
	@staticmethod
	def items_swapped(user_item: str, target_item: str) -> str:
		"""Mensagem de troca de itens."""
		if user_item and target_item:
			return f"   └─ 🎴 Itens trocados! ({user_item} ↔ {target_item})"
		elif user_item:
			return f"   └─ 🎴 {user_item} foi dado!"
		elif target_item:
			return f"   └─ 🎴 {target_item} foi recebido!"
		return "   └─ 🎴 Nenhum item para trocar!"
	
	@staticmethod
	def move_copied(user: str, move: str) -> str:
		"""Mensagem de cópia de movimento."""
		return f"   └─ 🎭 {user} copiou {move}!"
	
	@staticmethod
	def move_disabled(pokemon: str, move: str, turns: int) -> str:
		"""Mensagem de Disable."""
		return f"   └─ 🚫 {move} foi desabilitado! ({turns} turnos)"
	
	@staticmethod
	def move_encored(pokemon: str, move: str, turns: int) -> str:
		"""Mensagem de Encore."""
		return f"   └─ 👏 {pokemon} deve repetir {move}! ({turns} turnos)"
	
	@staticmethod
	def taunted(pokemon: str, turns: int) -> str:
		"""Mensagem de Taunt."""
		return f"   └─ 😤 {pokemon} foi provocado! ({turns} turnos)"
	
	@staticmethod
	def tormented(pokemon: str) -> str:
		"""Mensagem de Torment."""
		return f"   └─ 😈 {pokemon} não pode repetir movimentos!"
	
	@staticmethod
	def imprisoned(pokemon: str) -> str:
		"""Mensagem de Imprison."""
		return f"   └─ 🔒 Movimentos compartilhados foram selados!"
	
	@staticmethod
	def identified(pokemon: str) -> str:
		"""Mensagem de Foresight/Odor Sleuth."""
		return f"   └─ 👁️ {pokemon} foi identificado!"
	
	@staticmethod
	def miracle_eye(pokemon: str) -> str:
		"""Mensagem de Miracle Eye."""
		return f"   └─ 👁️ {pokemon} foi identificado por Miracle Eye!"
	
	# ==================== SPECIAL CONDITIONS ====================
	
	@staticmethod
	def perish_song(turns: int) -> str:
		"""Mensagem de Perish Song."""
		return f"   └─ 🎵 Todos vão desmaiar em {turns} turnos!"
	
	@staticmethod
	def perish_count(pokemon: str, count: int) -> str:
		"""Mensagem de contador de Perish Song."""
		return f"🎵 Perish count de {pokemon}: {count}"
	
	@staticmethod
	def destiny_bond_set(pokemon: str) -> str:
		"""Mensagem de Destiny Bond."""
		return f"   └─ 👻 {pokemon} quer levar o oponente junto!"
	
	@staticmethod
	def destiny_bond_activated(pokemon: str, target: str) -> str:
		"""Mensagem de ativação de Destiny Bond."""
		return f"👻 Destiny Bond! {target} também foi derrotado!"
	
	@staticmethod
	def grudge_set(pokemon: str) -> str:
		"""Mensagem de Grudge."""
		return f"   └─ 👻 {pokemon} guardará rancor!"
	
	@staticmethod
	def grudge_activated(move: str) -> str:
		"""Mensagem de ativação de Grudge."""
		return f"   └─ 👻 Grudge drenou todo o PP de {move}!"
	
	@staticmethod
	def yawning(pokemon: str) -> str:
		"""Mensagem de Yawn."""
		return f"   └─ 😴 {pokemon} está ficando com sono..."
	
	@staticmethod
	def nightmare_set(pokemon: str) -> str:
		"""Mensagem de Nightmare."""
		return f"   └─ 😱 {pokemon} está tendo pesadelos!"
	
	@staticmethod
	def curse_set(user: str, target: str) -> str:
		"""Mensagem de Curse (Ghost type)."""
		return f"   └─ 👻 {user} amaldiçoou {target} sacrificando metade de seu HP!"
	
	# ==================== RECHARGE & SPECIAL STATES ====================
	
	@staticmethod
	def must_recharge(pokemon: str) -> str:
		"""Mensagem de recarga obrigatória."""
		return f"⚡ {pokemon} precisa recarregar!"
	
	@staticmethod
	def charging_up(pokemon: str, move: str) -> str:
		"""Mensagem de carregamento (Razor Wind, etc)."""
		return f"⚡ {pokemon} está se preparando para {move}!"
	
	@staticmethod
	def semi_invulnerable(pokemon: str, move: str) -> str:
		"""Mensagem de semi-invulnerabilidade."""
		move_states = {
			"fly": "voou alto",
			"dig": "cavou fundo",
			"dive": "mergulhou",
			"bounce": "saltou alto",
			"phantom_force": "desapareceu",
			"shadow_force": "se escondeu nas sombras"
		}
		state = move_states.get(move, "ficou inacessível")
		return f"💨 {pokemon} {state}!"
	
	@staticmethod
	def focus_energy(pokemon: str) -> str:
		"""Mensagem de Focus Energy."""
		return f"   └─ 🎯 {pokemon} está concentrado!"
	
	@staticmethod
	def stockpile(pokemon: str, level: int) -> str:
		"""Mensagem de Stockpile."""
		return f"   └─ 📦 {pokemon} acumulou energia! (Nível {level})"
	
	@staticmethod
	def bide_start(pokemon: str) -> str:
		"""Mensagem de início de Bide."""
		return f"   └─ 😡 {pokemon} está acumulando energia!"
	
	@staticmethod
	def bide_unleash(pokemon: str, damage: int) -> str:
		"""Mensagem de liberação de Bide."""
		return f"😡 {pokemon} liberou {damage} de dano acumulado!"
	
	@staticmethod
	def rage_building(pokemon: str) -> str:
		"""Mensagem de Rage."""
		return f"   └─ 😡 A raiva de {pokemon} está crescendo!"
	
	# ==================== SWITCHING & ESCAPE ====================
	
	@staticmethod
	def cannot_escape(pokemon: str, reason: str = "") -> str:
		"""Mensagem quando não pode fugir."""
		if reason:
			return f"   └─ 🚫 {pokemon} não pode fugir! ({reason})"
		return f"   └─ 🚫 {pokemon} não pode fugir!"
	
	@staticmethod
	def teleported(pokemon: str) -> str:
		"""Mensagem de Teleport."""
		return f"   └─ ✨ {pokemon} teleportou!"
	
	@staticmethod
	def whirlwind(pokemon: str) -> str:
		"""Mensagem de Whirlwind/Roar."""
		return f"   └─ 🌪️ {pokemon} foi forçado a recuar!"
	
	@staticmethod
	def baton_pass(user: str) -> str:
		"""Mensagem de Baton Pass."""
		return f"   └─ 🎯 {user} passou seus efeitos!"
	
	@staticmethod
	def u_turn(user: str) -> str:
		"""Mensagem de U-turn/Volt Switch."""
		return f"   └─ 🔄 {user} voltou após o ataque!"
	
	# ==================== MISC ====================
	
	@staticmethod
	def critical_hit() -> str:
		"""Mensagem de critical hit."""
		return "💥 Um golpe crítico!"
	
	@staticmethod
	def super_effective() -> str:
		"""Mensagem de super eficaz."""
		return "✨ É super eficaz!"
	
	@staticmethod
	def not_very_effective() -> str:
		"""Mensagem de pouco eficaz."""
		return "💢 Não é muito eficaz..."
	
	@staticmethod
	def one_hit_ko() -> str:
		"""Mensagem de OHKO."""
		return "💀 Foi um nocaute instantâneo!"
	
	@staticmethod
	def endured(pokemon: str) -> str:
		"""Mensagem de Endure."""
		return f"💪 {pokemon} aguentou o golpe!"
	
	@staticmethod
	def protected_by_focus_sash(pokemon: str) -> str:
		"""Mensagem de Focus Sash/Sturdy."""
		return f"💪 {pokemon} aguentou com 1 HP!"
	
	@staticmethod
	def splash() -> str:
		"""Mensagem de Splash."""
		return "   └─ 💦 Mas nada aconteceu!"
	
	@staticmethod
	def pay_day(amount: int) -> str:
		"""Mensagem de Pay Day."""
		return f"   └─ 💰 Moedas foram espalhadas! (+${amount})"
	
	@staticmethod
	def coin_obtained(total: int) -> str:
		"""Mensagem de moedas obtidas."""
		return f"💰 Você obteve ${total}!"
	
	@staticmethod
	def experience_gained(pokemon: str, amount: int) -> str:
		"""Mensagem de XP ganho."""
		return f"⭐ {pokemon} ganhou {amount} XP!"
	
	@staticmethod
	def level_up(pokemon: str, new_level: int) -> str:
		"""Mensagem de level up."""
		return f"🎊 {pokemon} subiu para o nível {new_level}!"
	
	@staticmethod
	def learned_move(pokemon: str, move: str) -> str:
		"""Mensagem de movimento aprendido."""
		return f"📚 {pokemon} aprendeu **{move}**!"
	
	@staticmethod
	def forgot_move(pokemon: str, move: str) -> str:
		"""Mensagem de movimento esquecido."""
		return f"🗑️ {pokemon} esqueceu **{move}**!"
	
	@staticmethod
	def no_pp_left(pokemon: str, move: str) -> str:
		"""Mensagem de sem PP."""
		return f"❌ {pokemon} não tem PP para {move}!"
	
	@staticmethod
	def struggle_used(pokemon: str) -> str:
		"""Mensagem de Struggle."""
		return f"💢 {pokemon} não tem PP! Usou Struggle!"
