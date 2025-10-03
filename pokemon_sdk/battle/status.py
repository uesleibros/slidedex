import random
from typing import List, Tuple, Optional
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .messages import BattleMessages

class StatusHandler:
	
	@staticmethod
	def check_pre_action(user: BattlePokemon) -> Tuple[bool, List[str]]:
		if user.volatile.get("bide", 0) > 0:
			user.volatile["bide"] -= 1
			if user.volatile["bide"] == 0:
				return False, []
			return True, [f"⏳ {user.display_name} está acumulando energia..."]
		
		if user.volatile.get("uproar", 0) > 0:
			user.volatile["uproar"] -= 1
		
		if user.volatile["flinch"]:
			user.volatile["flinch"] = False
			return True, [f"💨 {user.display_name} recuou de medo!"]
		
		status = user.status["name"]
		counter = user.status["counter"]
		
		if status == "sleep":
			if user.volatile.get("nightmare"):
				dmg = max(1, user.stats["hp"] // 4)
				user.take_damage(dmg, ignore_substitute=True)
			
			if counter > 1:
				user.status["counter"] -= 1
				return True, [f"💤 {user.display_name} está dormindo..."]
			user.status = {"name": None, "counter": 0}
			user.volatile["nightmare"] = False
			return False, [f"👁️ {user.display_name} acordou!"]
		
		if status == "freeze":
			if random.random() < BattleConstants.FREEZE_THAW_CHANCE:
				user.status = {"name": None, "counter": 0}
				return False, [f"🔥 {user.display_name} descongelou!"]
			return True, [f"❄️ {user.display_name} está congelado!"]
		
		if status == "paralysis" and random.random() < BattleConstants.PARALYSIS_PROC_CHANCE:
			return True, [f"⚡ {user.display_name} está paralisado!"]
		
		return False, []
	
	@staticmethod
	def check_confusion(user: BattlePokemon) -> Tuple[bool, List[str]]:
		if user.volatile["confuse"] <= 0:
			return False, []
		
		user.volatile["confuse"] -= 1
		
		if user.volatile["confuse"] == 0:
			return False, [f"✨ {user.display_name} não está mais confuso!"]
		
		if random.random() < BattleConstants.CONFUSION_SELF_HIT_CHANCE:
			atk = user.eff_stat("atk")
			df = user.eff_stat("def")
			base = (((2 * user.level / 5) + 2) * 40 * (atk / max(1, df))) / 50 + 2
			dmg = max(1, int(base * random.uniform(BattleConstants.DAMAGE_ROLL_MIN, BattleConstants.DAMAGE_ROLL_MAX)))
			user.take_damage(dmg)
			return True, [f"😵 {user.display_name} se atingiu na confusão! ({dmg} de dano)"]
		
		return False, [f"😵 {user.display_name} está confuso..."]
	
	@staticmethod
	def apply_status_effect(target: BattlePokemon, effect_type: str) -> Optional[str]:
		from .helpers import _types_of
		tt = _types_of(target)
		
		immunity_checks = {
			"burn": ("fire", f"é do tipo Fogo"),
			"poison": (["steel", "poison"], f"é imune a veneno"),
			"freeze": ("ice", f"é do tipo Gelo")
		}
		
		if effect_type in immunity_checks:
			immune_types, message = immunity_checks[effect_type]
			immune_types = [immune_types] if isinstance(immune_types, str) else immune_types
			if any(t in tt for t in immune_types):
				return BattleMessages.immune(target.display_name, message)
		
		if target.set_status(effect_type):
			return BattleMessages.status_applied(target.display_name, effect_type)
		
		return BattleMessages.immune(target.display_name, "já está afetado")
	
	@staticmethod
	def end_of_turn_effects(player: BattlePokemon, wild: BattlePokemon) -> List[str]:
		lines = []
		
		for p, prefix in [(player, "🔵"), (wild, "🔴")]:
			if p.fainted:
				continue
			
			if p.volatile.get("wish", 0) > 0:
				p.volatile["wish"] -= 1
				if p.volatile["wish"] == 0:
					heal = p.volatile.get("wish_hp", 0)
					actual = p.heal(heal)
					if actual > 0:
						lines.append(f"⭐ O desejo de {p.display_name} se realizou! (+{actual} HP)")
			
			if p.volatile.get("yawn", 0) > 0:
				p.volatile["yawn"] -= 1
				if p.volatile["yawn"] == 0:
					if p.set_status("sleep"):
						lines.append(f"😴 {p.display_name} adormeceu de cansaço!")
			
			if p.volatile.get("perish_count", -1) > 0:
				p.volatile["perish_count"] -= 1
				if p.volatile["perish_count"] == 0:
					p.current_hp = 0
					lines.append(f"🎵 {p.display_name} sucumbiu ao Perish Song!")
				else:
					lines.append(f"🎵 {p.display_name} vai desmaiar em {p.volatile['perish_count']} turno(s)!")
			
			if p.volatile.get("ingrain"):
				heal = max(1, int(p.stats["hp"] * BattleConstants.INGRAIN_HEAL_RATIO))
				actual = p.heal(heal)
				if actual > 0:
					lines.append(f"🌿 {prefix} {p.display_name} absorveu {actual} HP!")
			
			if p.volatile.get("leech_seed"):
				leech_by = p.volatile.get("leech_seed_by")
				if leech_by and not leech_by.fainted:
					drain = max(1, int(p.stats["hp"] * BattleConstants.LEECH_SEED_RATIO))
					actual = p.take_damage(drain, ignore_substitute=True)
					healed = leech_by.heal(actual)
					lines.append(f"🌱 Leech Seed drenou {actual} HP de {p.display_name}!")
			
			status = p.status["name"]
			if status == "burn":
				d = max(1, int(p.stats["hp"] * BattleConstants.BURN_DAMAGE_RATIO))
				actual = p.take_damage(d, ignore_substitute=True)
				lines.append(f"🔥 {prefix} {p.display_name} sofreu {actual} de dano da queimadura")
			elif status == "poison":
				d = max(1, int(p.stats["hp"] * BattleConstants.POISON_DAMAGE_RATIO))
				actual = p.take_damage(d, ignore_substitute=True)
				lines.append(f"☠️ {prefix} {p.display_name} sofreu {actual} de dano do veneno")
			elif status == "toxic":
				p.status["counter"] += 1
				d = max(1, int(p.stats["hp"] * BattleConstants.TOXIC_BASE_RATIO) * p.status["counter"])
				actual = p.take_damage(d, ignore_substitute=True)
				lines.append(f"☠️☠️ {prefix} {p.display_name} sofreu {actual} de veneno grave!")
			
			for vol_key in ["light_screen", "reflect", "safeguard", "mist", "bind", "encore", "taunt", "disable"]:
				if p.volatile.get(vol_key, 0) > 0:
					p.volatile[vol_key] -= 1
					if p.volatile[vol_key] == 0:
						effect_names = {
							"light_screen": "Light Screen",
							"reflect": "Reflect",
							"safeguard": "Safeguard",
							"mist": "Névoa",
							"bind": "Bind",
							"encore": "Encore",
							"taunt": "Taunt",
							"disable": "Disable"
						}
						lines.append(f"⏱️ {effect_names[vol_key]} de {p.display_name} acabou!")
			
			p.clear_turn_volatiles()
			
			if p.fainted:
				lines.append(BattleMessages.fainted(p.display_name))
		
		return lines
