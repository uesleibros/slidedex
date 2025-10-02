import random
from typing import Dict, Any, List, Optional
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .messages import BattleMessages
from .status import StatusHandler

class EffectHandler:
    def apply_effect(
        self, 
        user: BattlePokemon, 
        target: BattlePokemon, 
        effect: Dict[str, Any], 
        damage_dealt: int
    ) -> List[str]:
        lines = []
        eff_type = effect.get("type")
        chance = effect.get("chance", 100)
        
        if chance < 100 and random.randint(1, 100) > chance:
            return lines
        
        tgt_type = effect.get("target", "opponent")
        actual_target = user if tgt_type == "self" else target
        
        handler_map = {
            "stat_change": self._handle_stat_change,
            "burn": lambda u, t, e, d: self._handle_status(t, "burn"),
            "poison": lambda u, t, e, d: self._handle_status(t, "poison"),
            "paralysis": lambda u, t, e, d: self._handle_status(t, "paralysis"),
            "sleep": lambda u, t, e, d: self._handle_status(t, "sleep"),
            "freeze": lambda u, t, e, d: self._handle_status(t, "freeze"),
            "toxic": lambda u, t, e, d: self._handle_status(t, "toxic"),
            "confusion": self._handle_confusion,
            "flinch": self._handle_flinch,
            "heal": self._handle_heal,
            "leech_seed": self._handle_leech_seed,
            "ingrain": self._handle_ingrain,
            "substitute": self._handle_substitute,
            "rest": self._handle_rest,
            "protect": self._handle_protect,
            "endure": self._handle_endure,
            "focus_energy": self._handle_focus_energy,
            "mist": self._handle_mist,
            "light_screen": self._handle_light_screen,
            "reflect": self._handle_reflect,
            "safeguard": self._handle_safeguard,
            "haze": self._handle_haze,
            "weather": self._handle_weather,
            "spikes": self._handle_spikes,
            "spite": self._handle_spite,
            "belly_drum": self._handle_belly_drum,
            "pain_split": self._handle_pain_split,
            "endeavor": self._handle_endeavor,
            "yawn": self._handle_yawn,
            "wish": self._handle_wish,
            "stockpile": self._handle_stockpile,
            "destiny_bond": self._handle_destiny_bond,
            "perish_song": self._handle_perish_song,
            "self_destruct": self._handle_self_destruct,
            "pay_day": self._handle_pay_day,
            "force_switch": self._handle_force_switch,
            "bind": self._handle_bind,
            "crash_damage": self._handle_crash_damage,
            "disable": self._handle_disable,
            "trap": self._handle_trap,
            "mind_reader": self._handle_mind_reader,
            "nightmare": self._handle_nightmare,
            "rage": self._handle_rage,
            "teleport": self._handle_teleport,
            "mimic": self._handle_mimic,
            "metronome": self._handle_metronome,
            "mirror_move": self._handle_mirror_move,
            "sketch": self._handle_sketch,
            "steal_item": self._handle_steal_item,
            "transform": self._handle_transform,
            "conversion": self._handle_conversion,
            "tri_attack": self._handle_tri_attack,
            "ancient_power": self._handle_ancient_power,
            "attract": self._handle_attract,
            "sleep_talk": self._handle_sleep_talk,
            "heal_bell": self._handle_heal_bell,
            "baton_pass": self._handle_baton_pass,
            "encore": self._handle_encore,
            "rapid_spin": self._handle_rapid_spin,
            "whirlpool": self._handle_whirlpool,
            "uproar_effect": self._handle_uproar_effect,
            "swallow": self._handle_swallow,
            "spit_up": self._handle_spit_up,
            "torment": self._handle_torment,
            "charge": self._handle_charge,
            "taunt": self._handle_taunt,
            "helping_hand": self._handle_helping_hand,
            "trick": self._handle_trick,
            "role_play": self._handle_role_play,
            "assist": self._handle_assist,
            "magic_coat": self._handle_magic_coat,
            "recycle": self._handle_recycle,
            "brick_break": self._handle_brick_break,
            "knock_off": self._handle_knock_off,
            "skill_swap": self._handle_skill_swap,
            "imprison": self._handle_imprison,
            "refresh": self._handle_refresh,
            "grudge": self._handle_grudge,
            "snatch": self._handle_snatch,
            "camouflage": self._handle_camouflage,
            "mud_sport": self._handle_mud_sport,
            "water_sport": self._handle_water_sport,
            "trick_room": self._handle_trick_room,
            "gravity": self._handle_gravity,
            "conversion2": self._handle_conversion2,
            "psych_up": self._handle_psych_up,
            "foresight": self._handle_foresight
        }
        
        handler = handler_map.get(eff_type)
        if handler:
            result = handler(user, actual_target, effect, damage_dealt)
            if result:
                lines.extend(result if isinstance(result, list) else [result])
        
        return lines
    
    def _handle_stat_change(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> Optional[List[str]]:
        stat = effect.get("stat")
        stages = effect.get("stages", 0)
        
        if not stat or stages == 0:
            return None
        
        was_protected_by_mist = target.volatile.get("mist", 0) > 0 and stages < 0
        
        actual_change, old_value = target.modify_stat_stage(stat, stages)
        
        if actual_change == 0:
            if was_protected_by_mist:
                return [f"   └─ 🌫️ A névoa protegeu {target.display_name}!"]
            elif old_value == BattleConstants.MAX_STAT_STAGE and stages > 0:
                return [BattleMessages.stat_maxed(target.display_name, stat, True)]
            elif old_value == BattleConstants.MIN_STAT_STAGE and stages < 0:
                return [BattleMessages.stat_maxed(target.display_name, stat, False)]
            else:
                return [BattleMessages.failed()]
        
        return [BattleMessages.stat_change(target.display_name, stat, actual_change)]
    
    def _handle_status(self, target: BattlePokemon, status: str) -> Optional[str]:
        return StatusHandler.apply_status_effect(target, status)
    
    def _handle_confusion(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["confuse"] = max(
            target.volatile["confuse"], 
            random.randint(BattleConstants.CONFUSION_MIN_TURNS, BattleConstants.CONFUSION_MAX_TURNS)
        )
        return f"   └─ 😵 {target.display_name} ficou confuso!"
    
    def _handle_flinch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> None:
        target.volatile["flinch"] = True
    
    def _handle_heal(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> Optional[str]:
        amount = effect.get("amount", 0.5)
        heal = max(1, int(user.stats["hp"] * amount))
        actual = user.heal(heal)
        if actual > 0:
            return BattleMessages.healing(user.display_name, actual)
        return None
    
    def _handle_leech_seed(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if "grass" not in target.types:
            target.volatile["leech_seed"] = True
            target.volatile["leech_seed_by"] = user
            return f"   └─ 🌱 {target.display_name} foi semeado!"
        return BattleMessages.immune(target.display_name, "é do tipo Grass")
    
    def _handle_ingrain(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["ingrain"] = True
        return f"   └─ 🌿 {user.display_name} criou raízes!"
    
    def _handle_substitute(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        hp_cost = int(user.stats["hp"] * effect.get("hp_cost", 0.25))
        if user.current_hp > hp_cost:
            user.current_hp -= hp_cost
            user.volatile["substitute"] = hp_cost
            return f"   └─ 🎭 {user.display_name} criou um substituto! (-{hp_cost} HP)"
        return BattleMessages.failed()
    
    def _handle_rest(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if user.current_hp < user.stats["hp"]:
            heal = user.stats["hp"] - user.current_hp
            user.current_hp = user.stats["hp"]
            user.status = {"name": "sleep", "counter": 2}
            return f"   └─ 💤 {user.display_name} dormiu e recuperou {heal} HP!"
        return BattleMessages.failed()
    
    def _handle_protect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["protect"] = True
        return f"   └─ 🛡️ {user.display_name} se protegeu!"
    
    def _handle_endure(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["endure"] = True
        return f"   └─ 💪 {user.display_name} vai aguentar!"
    
    def _handle_focus_energy(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["focus_energy"] = True
        return f"   └─ 🎯 {user.display_name} está se concentrando!"
    
    def _handle_mist(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["mist"] = effect.get("turns", 5)
        return f"   └─ 🌫️ Uma névoa protege {user.display_name}!"
    
    def _handle_light_screen(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["light_screen"] = effect.get("turns", 5)
        return f"   └─ ✨ Light Screen protege contra ataques especiais!"
    
    def _handle_reflect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["reflect"] = effect.get("turns", 5)
        return f"   └─ 🪞 Reflect protege contra ataques físicos!"
    
    def _handle_safeguard(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["safeguard"] = effect.get("turns", 5)
        return f"   └─ 🛡️ Safeguard protege contra status!"
    
    def _handle_haze(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.reset_stats()
        target.reset_stats()
        return f"   └─ 🌫️ Todos os stats foram resetados!"
    
    def _handle_weather(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        weather = effect.get("weather")
        weather_msgs = {
            "sun": "☀️ O sol está forte!", 
            "rain": "🌧️ Começou a chover!", 
            "hail": "❄️ Começou a gear!",
            "sandstorm": "🌪️ Uma tempestade de areia começou!"
        }
        return f"   └─ {weather_msgs.get(weather, '🌤️ O clima mudou!')}"
    
    def _handle_spikes(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> Optional[str]:
        return f"   └─ ⚠️ Spikes foram espalhados!"
    
    def _handle_spite(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> Optional[str]:
        if target.volatile.get("last_move_used"):
            pp_reduction = effect.get("pp_reduction", 4)
            move_id = target.volatile["last_move_used"]
            if target.dec_pp(move_id, pp_reduction):
                return f"   └─ 😈 PP do último golpe reduzido!"
        return None
    
    def _handle_belly_drum(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        hp_cost = int(user.stats["hp"] * effect.get("hp_cost", 0.5))
        if user.current_hp > hp_cost:
            user.current_hp -= hp_cost
            user.stages["atk"] = BattleConstants.MAX_STAT_STAGE
            return f"   └─ 🥁 {user.display_name} maximizou seu Ataque! (-{hp_cost} HP)"
        return BattleMessages.failed()
    
    def _handle_pain_split(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        avg = (user.current_hp + target.current_hp) // 2
        user.current_hp = avg
        target.current_hp = avg
        return f"   └─ 💔 HP foi dividido igualmente!"
    
    def _handle_endeavor(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> Optional[str]:
        if target.current_hp > user.current_hp:
            dmg = target.current_hp - user.current_hp
            target.take_damage(dmg)
            return f"   └─ 💢 HP do oponente igualado! ({dmg} de dano)"
        return None
    
    def _handle_yawn(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["yawn"] = 1
        return f"   └─ 😴 {target.display_name} está ficando com sono..."
    
    def _handle_wish(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["wish"] = 1
        user.volatile["wish_hp"] = user.stats["hp"] // 2
        return f"   └─ ⭐ {user.display_name} fez um desejo!"
    
    def _handle_stockpile(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if user.volatile["stockpile"] < 3:
            user.volatile["stockpile"] += 1
            return f"   └─ 📦 Energia acumulada! (Nível {user.volatile['stockpile']})"
        return BattleMessages.failed()
    
    def _handle_destiny_bond(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["destiny_bond"] = True
        return f"   └─ 👻 {user.display_name} quer levar o oponente junto!"
    
    def _handle_perish_song(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["perish_count"] = 3
        target.volatile["perish_count"] = 3
        return f"   └─ 🎵 Todos vão desmaiar em 3 turnos!"
    
    def _handle_self_destruct(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.current_hp = 0
        return f"   └─ 💥 {user.display_name} se sacrificou!"
    
    def _handle_pay_day(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 💰 Moedas espalhadas pelo campo!"
    
    def _handle_force_switch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🌀 {target.display_name} foi forçado a recuar!"
    
    def _handle_bind(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        min_turns = effect.get("min_turns", 2)
        max_turns = effect.get("max_turns", 5)
        turns = random.randint(min_turns, max_turns)
        target.volatile["bind"] = turns
        target.volatile["bind_by"] = user
        return f"   └─ 🎯 {target.display_name} foi preso por {turns} turnos!"
    
    def _handle_crash_damage(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 💥 {user.display_name} errou e se machucou!"
    
    def _handle_disable(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if target.volatile.get("last_move_used"):
            min_turns = effect.get("min_turns", 1)
            max_turns = effect.get("max_turns", 8)
            turns = random.randint(min_turns, max_turns)
            target.volatile["disable"] = turns
            target.volatile["disable_move"] = target.volatile["last_move_used"]
            return f"   └─ 🚫 Último movimento foi desabilitado!"
        return BattleMessages.failed()
    
    def _handle_trap(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["trapped"] = True
        return f"   └─ 🕸️ {target.display_name} não pode fugir!"
    
    def _handle_mind_reader(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["mind_reader_target"] = target
        return f"   └─ 👁️ {user.display_name} mirou em {target.display_name}!"
    
    def _handle_nightmare(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if target.status["name"] == "sleep":
            target.volatile["nightmare"] = True
            return f"   └─ 😱 {target.display_name} está tendo pesadelos!"
        return BattleMessages.failed()
    
    def _handle_rage(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["rage"] = True
        return f"   └─ 😡 {user.display_name} entrou em fúria!"
    
    def _handle_teleport(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ ✨ {user.display_name} escapou!"
    
    def _handle_mimic(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if target.volatile.get("last_move_used"):
            return f"   └─ 🎭 {user.display_name} copiou o movimento!"
        return BattleMessages.failed()
    
    def _handle_metronome(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🎲 Metronome ativado!"
    
    def _handle_mirror_move(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if target.volatile.get("last_move_used"):
            return f"   └─ 🪞 {user.display_name} espelhou o movimento!"
        return BattleMessages.failed()
    
    def _handle_sketch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if target.volatile.get("last_move_used"):
            return f"   └─ ✏️ {user.display_name} esboçou o movimento!"
        return BattleMessages.failed()
    
    def _handle_steal_item(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🎯 {user.display_name} roubou o item!"
    
    def _handle_transform(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔄 {user.display_name} se transformou em {target.display_name}!"
    
    def _handle_conversion(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔀 {user.display_name} mudou de tipo!"
    
    def _handle_tri_attack(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> Optional[str]:
        statuses = ["burn", "freeze", "paralysis"]
        chosen = random.choice(statuses)
        result = StatusHandler.apply_status_effect(target, chosen)
        return result
    
    def _handle_ancient_power(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        stats = ["atk", "def", "sp_atk", "sp_def", "speed"]
        for stat in stats:
            user.stages[stat] = min(BattleConstants.MAX_STAT_STAGE, user.stages[stat] + 1)
        return f"   └─ ✨ Todos os stats de {user.display_name} aumentaram!"
    
    def _handle_attract(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 💕 {target.display_name} se apaixonou!"
    
    def _handle_sleep_talk(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 💤 {user.display_name} usou um movimento dormindo!"
    
    def _handle_heal_bell(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔔 Todos os aliados foram curados de status!"
    
    def _handle_baton_pass(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🎯 {user.display_name} passou seus efeitos!"
    
    def _handle_encore(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        if target.volatile.get("last_move_used"):
            min_turns = effect.get("min_turns", 2)
            max_turns = effect.get("max_turns", 6)
            turns = random.randint(min_turns, max_turns)
            target.volatile["encore"] = turns
            target.volatile["encore_move"] = target.volatile["last_move_used"]
            return f"   └─ 👏 {target.display_name} foi forçado a repetir!"
        return BattleMessages.failed()
    
    def _handle_rapid_spin(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["leech_seed"] = False
        user.volatile["bind"] = 0
        return f"   └─ 🌀 {user.display_name} se libertou!"
    
    def _handle_whirlpool(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        min_turns = effect.get("min_turns", 2)
        max_turns = effect.get("max_turns", 5)
        turns = random.randint(min_turns, max_turns)
        target.volatile["bind"] = turns
        target.volatile["bind_by"] = user
        return f"   └─ 🌊 {target.display_name} foi preso no redemoinho!"
    
    def _handle_uproar_effect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["uproar"] = 3
        return f"   └─ 📢 {user.display_name} causou alvoroço!"
    
    def _handle_swallow(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        stockpile = user.volatile.get("stockpile", 0)
        if stockpile == 0:
            return BattleMessages.failed()
        
        heal_ratios = {1: 0.25, 2: 0.5, 3: 1.0}
        heal_amount = int(user.stats["hp"] * heal_ratios.get(stockpile, 0.25))
        actual = user.heal(heal_amount)
        user.volatile["stockpile"] = 0
        return f"   └─ 💚 {user.display_name} recuperou {actual} HP!"
    
    def _handle_spit_up(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        stockpile = user.volatile.get("stockpile", 0)
        if stockpile == 0:
            return BattleMessages.failed()
        user.volatile["stockpile"] = 0
        return f"   └─ 💥 Liberou {stockpile} níveis de energia!"
    
    def _handle_torment(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["torment"] = True
        return f"   └─ 😈 {target.display_name} não pode repetir movimentos!"
    
    def _handle_charge(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["charge"] = True
        return f"   └─ ⚡ {user.display_name} está carregando!"
    
    def _handle_taunt(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["taunt"] = 3
        return f"   └─ 😤 {target.display_name} foi provocado!"
    
    def _handle_helping_hand(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🤝 {user.display_name} está ajudando!"
    
    def _handle_trick(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🎴 Itens foram trocados!"
    
    def _handle_role_play(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🎭 {user.display_name} copiou a habilidade!"
    
    def _handle_assist(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🆘 {user.display_name} usou um movimento aliado!"
    
    def _handle_magic_coat(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["magic_coat"] = True
        return f"   └─ ✨ {user.display_name} refletirá efeitos!"
    
    def _handle_recycle(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ ♻️ {user.display_name} recuperou seu item!"
    
    def _handle_brick_break(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["light_screen"] = 0
        target.volatile["reflect"] = 0
        return f"   └─ 🥋 Barreiras foram destruídas!"
    
    def _handle_knock_off(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 👊 O item foi derrubado!"
    
    def _handle_skill_swap(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔄 Habilidades foram trocadas!"
    
    def _handle_imprison(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔒 Movimentos compartilhados foram selados!"
    
    def _handle_refresh(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        cured = []
        if user.status["name"] in ["burn", "paralysis", "poison", "toxic"]:
            cured.append(user.status["name"])
            user.status = {"name": None, "counter": 0}
        
        if cured:
            return f"   └─ 💫 {user.display_name} curou {', '.join(cured)}!"
        return BattleMessages.failed()
    
    def _handle_grudge(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["grudge"] = True
        return f"   └─ 👻 {user.display_name} guardará rancor!"
    
    def _handle_snatch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        user.volatile["snatch"] = True
        return f"   └─ 🎯 {user.display_name} está esperando para roubar!"
    
    def _handle_camouflage(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🦎 {user.display_name} se camuflou!"
    
    def _handle_mud_sport(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ ⚡ Dano elétrico foi reduzido!"
    
    def _handle_water_sport(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔥 Dano de fogo foi reduzido!"
    
    def _handle_trick_room(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔄 Trick Room foi ativado!"
    
    def _handle_gravity(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ ⬇️ Gravidade foi intensificada!"
    
    def _handle_conversion2(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        return f"   └─ 🔀 {user.display_name} mudou de tipo defensivamente!"
    
    def _handle_psych_up(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        for stat in ["atk", "def", "sp_atk", "sp_def", "speed", "accuracy", "evasion"]:
            user.stages[stat] = target.stages[stat]
        return f"   └─ 🧠 {user.display_name} copiou as mudanças de stats!"
    
    def _handle_foresight(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int) -> str:
        target.volatile["foresight"] = True
        target.stages["evasion"] = 0
        return f"   └─ 👁️ {target.display_name} foi identificado!"
