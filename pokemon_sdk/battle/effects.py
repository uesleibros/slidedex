import random
from typing import Dict, Any, List, Optional
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .messages import BattleMessages
from .status import StatusHandler
from .helpers import MoveData

class EffectHandler:
    def apply_effect(
        self, 
        user: BattlePokemon, 
        target: BattlePokemon, 
        effect: Dict[str, Any], 
        damage_dealt: int,
        move_data: Optional[MoveData] = None
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
            "burn": lambda u, t, e, d, m: self._handle_status(t, "burn"),
            "poison": lambda u, t, e, d, m: self._handle_status(t, "poison"),
            "paralysis": lambda u, t, e, d, m: self._handle_status(t, "paralysis"),
            "sleep": lambda u, t, e, d, m: self._handle_status(t, "sleep"),
            "freeze": lambda u, t, e, d, m: self._handle_status(t, "freeze"),
            "toxic": lambda u, t, e, d, m: self._handle_status(t, "toxic"),
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
            "foresight": self._handle_foresight,
            "nothing": self._handle_nothing
        }
        
        handler = handler_map.get(eff_type)
        if handler:
            result = handler(user, actual_target, effect, damage_dealt, move_data)
            if result:
                lines.extend(result if isinstance(result, list) else [result])
        
        return lines
    
    def _handle_stat_change(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[List[str]]:
        stat = effect.get("stat")
        stages = effect.get("stages", 0)
        
        if not stat or stages == 0:
            return None
        
        was_protected_by_mist = target.volatile.get("mist", 0) > 0 and stages < 0
        
        actual_change, old_value = target.modify_stat_stage(stat, stages)
        
        if actual_change == 0:
            if was_protected_by_mist:
                return [BattleMessages.protected_by_mist(target.display_name)]
            elif old_value == BattleConstants.MAX_STAT_STAGE and stages > 0:
                return [BattleMessages.stat_maxed(target.display_name, stat, True)]
            elif old_value == BattleConstants.MIN_STAT_STAGE and stages < 0:
                return [BattleMessages.stat_maxed(target.display_name, stat, False)]
            else:
                return [BattleMessages.failed()]
        
        return [BattleMessages.stat_change(target.display_name, stat, actual_change)]
    
    def _handle_status(self, target: BattlePokemon, status: str) -> Optional[str]:
        return StatusHandler.apply_status_effect(target, status)
    
    def _handle_confusion(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[str]:
        if target.volatile.get("confuse", 0) > 0:
            return None
        
        target.volatile["confuse"] = random.randint(
            BattleConstants.CONFUSION_MIN_TURNS, 
            BattleConstants.CONFUSION_MAX_TURNS
        )
        return BattleMessages.confused(target.display_name)
    
    def _handle_flinch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> None:
        target.volatile["flinch"] = True
    
    def _handle_heal(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[str]:
        if user.current_hp >= user.stats["hp"]:
            return BattleMessages.failed()
        
        amount = effect.get("amount", 0.5)
        heal = max(1, int(user.stats["hp"] * amount))
        actual = user.heal(heal)
        
        if actual > 0:
            return BattleMessages.healing(user.display_name, actual)
        return None
    
    def _handle_leech_seed(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("leech_seed"):
            return BattleMessages.failed()
        
        if "grass" in target.types:
            return BattleMessages.immune(target.display_name, "é do tipo Grass")
        
        target.volatile["leech_seed"] = True
        target.volatile["leech_seed_by"] = user
        return BattleMessages.seeded(target.display_name)
    
    def _handle_ingrain(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("ingrain"):
            return BattleMessages.failed()
        
        user.volatile["ingrain"] = True
        return "   └─ 🌿 " + user.display_name + " criou raízes!"
    
    def _handle_substitute(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("substitute", 0) > 0:
            return BattleMessages.failed()
        
        hp_cost = max(1, int(user.stats["hp"] * effect.get("hp_cost", 0.25)))
        
        if user.current_hp <= hp_cost:
            return BattleMessages.failed()
        
        user.current_hp -= hp_cost
        user.volatile["substitute"] = hp_cost
        return BattleMessages.substitute_made(user.display_name, hp_cost)
    
    def _handle_rest(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.current_hp >= user.stats["hp"]:
            return BattleMessages.failed()
        
        heal = user.stats["hp"] - user.current_hp
        user.current_hp = user.stats["hp"]
        user.status = {"name": "sleep", "counter": 2}
        return f"   └─ 💤 {user.display_name} dormiu e recuperou {heal} HP!"
    
    def _handle_protect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["protect"] = True
        return f"   └─ 🛡️ {user.display_name} se protegeu!"
    
    def _handle_endure(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["endure"] = True
        return f"   └─ 💪 {user.display_name} vai aguentar!"
    
    def _handle_focus_energy(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("focus_energy"):
            return BattleMessages.failed()
        
        user.volatile["focus_energy"] = True
        return BattleMessages.focus_energy(user.display_name)
    
    def _handle_mist(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("mist", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 5)
        user.volatile["mist"] = turns
        return BattleMessages.mist_set(turns)
    
    def _handle_light_screen(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("light_screen", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 5)
        user.volatile["light_screen"] = turns
        return BattleMessages.light_screen_set(turns)
    
    def _handle_reflect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("reflect", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 5)
        user.volatile["reflect"] = turns
        return BattleMessages.reflect_set(turns)
    
    def _handle_safeguard(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("safeguard", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 5)
        user.volatile["safeguard"] = turns
        return BattleMessages.safeguard_set(turns)
    
    def _handle_haze(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.reset_stats()
        target.reset_stats()
        return BattleMessages.stats_reset(all_pokemon=True)
    
    def _handle_weather(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        weather = effect.get("weather")
        turns = effect.get("turns", 5)
        user.volatile["weather"] = weather
        user.volatile["weather_turns"] = turns
        return BattleMessages.weather_started(weather, turns)
    
    def _handle_spikes(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[str]:
        spikes_count = target.volatile.get("spikes_layers", 0)
        
        if spikes_count >= 3:
            return BattleMessages.failed()
        
        target.volatile["spikes_layers"] = spikes_count + 1
        return BattleMessages.spikes_set(spikes_count + 1)
    
    def _handle_spite(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[str]:
        last_move = target.volatile.get("last_move_used")
        
        if not last_move:
            return BattleMessages.failed()
        
        pp_reduction = effect.get("pp_reduction", 4)
        
        if hasattr(target, 'dec_pp') and target.dec_pp(last_move, pp_reduction):
            return f"   └─ 😈 PP do último golpe reduzido em {pp_reduction}!"
        
        return BattleMessages.failed()
    
    def _handle_belly_drum(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.stages["atk"] >= BattleConstants.MAX_STAT_STAGE:
            return BattleMessages.failed()
        
        hp_cost = max(1, int(user.stats["hp"] * effect.get("hp_cost", 0.5)))
        
        if user.current_hp <= hp_cost:
            return BattleMessages.failed()
        
        user.current_hp -= hp_cost
        user.stages["atk"] = BattleConstants.MAX_STAT_STAGE
        return f"   └─ 🥁 {user.display_name} maximizou seu Ataque! (-{hp_cost} HP)"
    
    def _handle_pain_split(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        avg = (user.current_hp + target.current_hp) // 2
        user.current_hp = min(avg, user.stats["hp"])
        target.current_hp = min(avg, target.stats["hp"])
        return f"   └─ 💔 HP foi dividido igualmente! ({avg} HP cada)"
    
    def _handle_endeavor(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[str]:
        if target.current_hp <= user.current_hp:
            return BattleMessages.failed()
        
        dmg = target.current_hp - user.current_hp
        target.take_damage(dmg)
        return f"   └─ 💢 HP do oponente igualado! ({dmg} de dano)"
    
    def _handle_yawn(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.status["name"] or target.volatile.get("yawn", 0) > 0:
            return BattleMessages.failed()
        
        target.volatile["yawn"] = 1
        return BattleMessages.yawning(target.display_name)
    
    def _handle_wish(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("wish", 0) > 0:
            return BattleMessages.failed()
        
        user.volatile["wish"] = 1
        user.volatile["wish_hp"] = user.stats["hp"] // 2
        return f"   └─ ⭐ {user.display_name} fez um desejo!"
    
    def _handle_stockpile(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        stockpile = user.volatile.get("stockpile", 0)
        
        if stockpile >= 3:
            return BattleMessages.failed()
        
        user.volatile["stockpile"] = stockpile + 1
        user.modify_stat_stage("def", 1)
        user.modify_stat_stage("sp_def", 1)
        
        return BattleMessages.stockpile(user.display_name, stockpile + 1)
    
    def _handle_destiny_bond(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["destiny_bond"] = True
        return BattleMessages.destiny_bond_set(user.display_name)
    
    def _handle_perish_song(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["perish_count"] = 3
        target.volatile["perish_count"] = 3
        return BattleMessages.perish_song(3)
    
    def _handle_self_destruct(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.current_hp = 0
        return f"   └─ 💥 {user.display_name} se sacrificou!"
    
    def _handle_pay_day(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        money = effect.get("money_multiplier", 5) * user.level
        user.volatile["pay_day_money"] = user.volatile.get("pay_day_money", 0) + money
        return BattleMessages.pay_day(money)
    
    def _handle_force_switch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("ingrain") or target.volatile.get("trapped"):
            return BattleMessages.failed()
        
        target.volatile["force_switch"] = True
        return BattleMessages.whirlwind(target.display_name)
    
    def _handle_bind(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("bind", 0) > 0:
            return BattleMessages.failed()
        
        min_turns = effect.get("min_turns", 2)
        max_turns = effect.get("max_turns", 5)
        turns = random.randint(min_turns, max_turns)
        
        if move_data and move_data.name:
            move_name = move_data.name
        else:
            move_name = "Bind"
        
        target.volatile["bind"] = turns
        target.volatile["bind_by"] = user
        target.volatile["bind_damage"] = max(1, user.stats["hp"] // 16)
        target.volatile["bind_type"] = move_name
        
        return BattleMessages.bound(target.display_name, turns, move_name)
    
    def _handle_crash_damage(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        crash_percent = effect.get("crash_percent", 0.5)
        crash_dmg = max(1, int(user.stats["hp"] * crash_percent))
        user.take_damage(crash_dmg)
        return f"   └─ 💥 {user.display_name} errou e se machucou! ({crash_dmg} de dano)"
    
    def _handle_disable(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        last_move = target.volatile.get("last_move_used")
        
        if not last_move or target.volatile.get("disable", 0) > 0:
            return BattleMessages.failed()
        
        min_turns = effect.get("min_turns", 1)
        max_turns = effect.get("max_turns", 8)
        turns = random.randint(min_turns, max_turns)
        
        target.volatile["disable"] = turns
        target.volatile["disable_move"] = last_move
        
        move_name = last_move.replace("_", " ").title()
        return BattleMessages.move_disabled(target.display_name, move_name, turns)
    
    def _handle_trap(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("trapped"):
            return BattleMessages.failed()
        
        target.volatile["trapped"] = True
        target.volatile["trapped_by"] = user
        return BattleMessages.trapped(target.display_name)
    
    def _handle_mind_reader(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["mind_reader_target"] = target
        user.volatile["mind_reader_turns"] = 1
        return f"   └─ 👁️ {user.display_name} mirou em {target.display_name}!"
    
    def _handle_nightmare(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.status.get("name") != "sleep":
            return BattleMessages.failed()
        
        if target.volatile.get("nightmare"):
            return BattleMessages.failed()
        
        target.volatile["nightmare"] = True
        return BattleMessages.nightmare_set(target.display_name)
    
    def _handle_rage(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["rage"] = True
        user.volatile["rage_active"] = True
        return f"   └─ 😡 {user.display_name} entrou em fúria!"
    
    def _handle_teleport(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["teleport"] = True
        user.volatile["fled"] = True
        return BattleMessages.teleported(user.display_name)
    
    def _handle_mimic(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        last_move = target.volatile.get("last_move_used")
        
        if not last_move:
            return BattleMessages.failed()
        
        if hasattr(user, 'moves') and last_move in [m.get('id') for m in user.moves]:
            return BattleMessages.failed()
        
        user.volatile["mimic_move"] = last_move
        user.volatile["mimic_pp"] = 5
        
        move_name = last_move.replace("_", " ").title()
        return BattleMessages.move_copied(user.display_name, move_name)
    
    def _handle_metronome(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["metronome_active"] = True
        return f"   └─ 🎲 Metronome selecionou um movimento aleatório!"
    
    def _handle_mirror_move(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        last_move = target.volatile.get("last_move_used")
        
        if not last_move:
            return BattleMessages.failed()
        
        user.volatile["mirror_move"] = last_move
        move_name = last_move.replace("_", " ").title()
        return BattleMessages.move_copied(user.display_name, move_name)
    
    def _handle_sketch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        last_move = target.volatile.get("last_move_used")
        
        if not last_move:
            return BattleMessages.failed()
        
        if hasattr(user, 'moves') and last_move in [m.get('id') for m in user.moves]:
            return BattleMessages.failed()
        
        user.volatile["sketch_move"] = last_move
        user.volatile["sketch_learned"] = True
        
        move_name = last_move.replace("_", " ").title()
        return f"   └─ ✏️ {user.display_name} esboçou {move_name} permanentemente!"
    
    def _handle_steal_item(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        target_item = target.volatile.get("held_item")
        
        if not target_item or user.volatile.get("held_item"):
            return BattleMessages.failed()
        
        user.volatile["held_item"] = target_item
        target.volatile["held_item"] = None
        target.volatile["stolen_item"] = target_item
        
        return BattleMessages.item_stolen(user.display_name, target_item, target.display_name)
    
    def _handle_transform(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("transformed"):
            return BattleMessages.failed()
        
        user.volatile["original_stats"] = user.stats.copy()
        user.volatile["original_types"] = user.types.copy()
        user.volatile["original_moves"] = user.moves.copy() if hasattr(user, 'moves') else []
        
        user.stats = target.stats.copy()
        user.types = target.types.copy()
        user.stages = target.stages.copy()
        
        if hasattr(target, 'moves'):
            user.moves = target.moves.copy()
        
        user.volatile["transformed"] = True
        user.volatile["transform_target"] = target.display_name
        
        return BattleMessages.transformed(user.display_name, target.display_name)
    
    def _handle_conversion(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if not hasattr(user, 'moves') or not user.moves:
            return BattleMessages.failed()
        
        first_move = user.moves[0]
        move_type = first_move.get("type", "normal")
        
        if move_type in user.types:
            return BattleMessages.failed()
        
        user.volatile["original_types"] = user.types.copy()
        user.types = [move_type]
        user.volatile["conversion_type"] = move_type
        
        return BattleMessages.type_changed(user.display_name, move_type)
    
    def _handle_tri_attack(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> Optional[str]:
        statuses = ["burn", "freeze", "paralysis"]
        chosen = random.choice(statuses)
        result = StatusHandler.apply_status_effect(target, chosen)
        return result
    
    def _handle_ancient_power(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        stats = ["atk", "def", "sp_atk", "sp_def", "speed"]
        changes = []
        
        for stat in stats:
            actual_change, _ = user.modify_stat_stage(stat, 1)
            if actual_change > 0:
                changes.append(stat)
        
        if changes:
            return f"   └─ ✨ Todos os stats de {user.display_name} aumentaram!"
        
        return BattleMessages.failed()
    
    def _handle_attract(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("attract"):
            return BattleMessages.failed()
        
        if hasattr(user, 'gender') and hasattr(target, 'gender'):
            if user.gender == target.gender or user.gender is None or target.gender is None:
                return BattleMessages.failed()
        
        target.volatile["attract"] = True
        target.volatile["attract_by"] = user
        
        return BattleMessages.attracted(target.display_name, user.display_name)
    
    def _handle_sleep_talk(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.status.get("name") != "sleep":
            return BattleMessages.failed()
        
        if not hasattr(user, 'moves') or not user.moves:
            return BattleMessages.failed()
        
        available_moves = [m for m in user.moves if m.get('id') != 'sleep_talk']
        
        if not available_moves:
            return BattleMessages.failed()
        
        selected_move = random.choice(available_moves)
        user.volatile["sleep_talk_move"] = selected_move.get('id')
        
        return f"   └─ 💤 {user.display_name} usou {selected_move.get('name', 'um movimento')} dormindo!"
    
    def _handle_heal_bell(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        cured = False
        
        if user.status.get("name"):
            user.status = {"name": None, "counter": 0}
            cured = True
        
        user.volatile["heal_bell_used"] = True
        
        if cured:
            return f"   └─ 🔔 {user.display_name} e aliados foram curados de status!"
        
        return f"   └─ 🔔 Sino de cura tocou!"
    
    def _handle_baton_pass(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        effects_to_pass = {}
        
        passable_effects = [
            "substitute", "focus_energy", "leech_seed", "confuse",
            "aqua_ring", "ingrain", "attract"
        ]
        
        effects_to_pass["stages"] = user.stages.copy()
        
        for eff in passable_effects:
            if user.volatile.get(eff):
                effects_to_pass[eff] = user.volatile[eff]
        
        user.volatile["baton_pass_effects"] = effects_to_pass
        user.volatile["baton_pass_active"] = True
        user.volatile["force_switch"] = True
        
        return BattleMessages.baton_pass(user.display_name)
    
    def _handle_encore(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        last_move = target.volatile.get("last_move_used")
        
        if not last_move or target.volatile.get("encore", 0) > 0:
            return BattleMessages.failed()
        
        min_turns = effect.get("min_turns", 2)
        max_turns = effect.get("max_turns", 6)
        turns = random.randint(min_turns, max_turns)
        
        target.volatile["encore"] = turns
        target.volatile["encore_move"] = last_move
        
        move_name = last_move.replace("_", " ").title()
        return BattleMessages.move_encored(target.display_name, move_name, turns)
    
    def _handle_rapid_spin(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        removed_effects = []
        
        if user.volatile.get("leech_seed"):
            user.volatile["leech_seed"] = False
            removed_effects.append("Leech Seed")
        
        if user.volatile.get("bind", 0) > 0:
            user.volatile["bind"] = 0
            removed_effects.append("Bind")
        
        if user.volatile.get("spikes_layers", 0) > 0:
            user.volatile["spikes_layers"] = 0
            removed_effects.append("Spikes")
        
        if removed_effects:
            return f"   └─ 🌀 {user.display_name} se libertou de {', '.join(removed_effects)}!"
        
        return f"   └─ 🌀 {user.display_name} girou rapidamente!"
    
    def _handle_whirlpool(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("bind", 0) > 0:
            return BattleMessages.failed()
        
        min_turns = effect.get("min_turns", 2)
        max_turns = effect.get("max_turns", 5)
        turns = random.randint(min_turns, max_turns)
        
        if move_data and move_data.name:
            move_name = move_data.name
        else:
            move_name = "Whirlpool"
        
        target.volatile["bind"] = turns
        target.volatile["bind_by"] = user
        target.volatile["bind_damage"] = max(1, target.stats["hp"] // 16)
        target.volatile["bind_type"] = move_name
        
        return BattleMessages.bound(target.display_name, turns, move_name)
    
    def _handle_uproar_effect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("uproar", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 3)
        user.volatile["uproar"] = turns
        user.volatile["uproar_active"] = True
        
        return f"   └─ 📢 {user.display_name} causou alvoroço por {turns} turnos!"
    
    def _handle_swallow(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        stockpile = user.volatile.get("stockpile", 0)
        
        if stockpile == 0:
            return BattleMessages.failed()
        
        if user.current_hp >= user.stats["hp"]:
            return BattleMessages.failed()
        
        heal_ratios = {1: 0.25, 2: 0.5, 3: 1.0}
        heal_amount = int(user.stats["hp"] * heal_ratios.get(stockpile, 0.25))
        actual = user.heal(heal_amount)
        
        user.volatile["stockpile"] = 0
        user.modify_stat_stage("def", -stockpile)
        user.modify_stat_stage("sp_def", -stockpile)
        
        return BattleMessages.healing(user.display_name, actual)
    
    def _handle_spit_up(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        stockpile = user.volatile.get("stockpile", 0)
        
        if stockpile == 0:
            return BattleMessages.failed()
        
        user.volatile["spit_up_power"] = 100 * stockpile
        
        user.volatile["stockpile"] = 0
        user.modify_stat_stage("def", -stockpile)
        user.modify_stat_stage("sp_def", -stockpile)
        
        return f"   └─ 💥 Liberou {stockpile} níveis de energia!"
    
    def _handle_torment(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("torment"):
            return BattleMessages.failed()
        
        target.volatile["torment"] = True
        return BattleMessages.tormented(target.display_name)
    
    def _handle_charge(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("charge"):
            return BattleMessages.failed()
        
        user.volatile["charge"] = True
        user.volatile["charge_turns"] = 1
        user.modify_stat_stage("sp_def", 1)
        
        return f"   └─ ⚡ {user.display_name} está carregando poder elétrico!"
    
    def _handle_taunt(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("taunt", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 3)
        target.volatile["taunt"] = turns
        
        return BattleMessages.taunted(target.display_name, turns)
    
    def _handle_helping_hand(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["helping_hand"] = True
        user.volatile["helping_hand_target"] = target
        
        return f"   └─ 🤝 {user.display_name} está ajudando {target.display_name}!"
    
    def _handle_trick(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user_item = user.volatile.get("held_item")
        target_item = target.volatile.get("held_item")
        
        user.volatile["held_item"] = target_item
        target.volatile["held_item"] = user_item
        
        user.volatile["trick_used"] = True
        target.volatile["trick_target"] = True
        
        return BattleMessages.items_swapped(user_item, target_item)
    
    def _handle_role_play(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        target_ability = getattr(target, 'ability', None)
        
        if not target_ability:
            return BattleMessages.failed()
        
        uncopyable = ["wonder_guard", "multitype", "stance_change"]
        
        if target_ability in uncopyable:
            return BattleMessages.failed()
        
        user.volatile["original_ability"] = getattr(user, 'ability', None)
        user.ability = target_ability
        user.volatile["role_play_ability"] = target_ability
        
        return BattleMessages.ability_copied(user.display_name, target_ability, target.display_name)
    
    def _handle_assist(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["assist_active"] = True
        
        return f"   └─ 🆘 {user.display_name} usou um movimento aliado!"
    
    def _handle_magic_coat(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["magic_coat"] = True
        user.volatile["magic_coat_turns"] = 1
        
        return f"   └─ ✨ {user.display_name} refletirá movimentos de status!"
    
    def _handle_recycle(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        used_item = user.volatile.get("used_item") or user.volatile.get("stolen_item")
        
        if not used_item or user.volatile.get("held_item"):
            return BattleMessages.failed()
        
        user.volatile["held_item"] = used_item
        user.volatile["recycled_item"] = used_item
        
        return f"   └─ ♻️ {user.display_name} recuperou {used_item}!"
    
    def _handle_brick_break(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        removed = []
        
        if target.volatile.get("light_screen", 0) > 0:
            target.volatile["light_screen"] = 0
            removed.append("Light Screen")
        
        if target.volatile.get("reflect", 0) > 0:
            target.volatile["reflect"] = 0
            removed.append("Reflect")
        
        if removed:
            return f"   └─ 🥋 {', '.join(removed)} foram destruídas!"
        
        return None
    
    def _handle_knock_off(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        target_item = target.volatile.get("held_item")
        
        if not target_item:
            return BattleMessages.failed()
        
        target.volatile["held_item"] = None
        target.volatile["knocked_off_item"] = target_item
        
        return BattleMessages.item_knocked_off(target.display_name, target_item)
    
    def _handle_skill_swap(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user_ability = getattr(user, 'ability', None)
        target_ability = getattr(target, 'ability', None)
        
        if not user_ability or not target_ability:
            return BattleMessages.failed()
        
        unswappable = ["wonder_guard", "multitype", "stance_change"]
        
        if user_ability in unswappable or target_ability in unswappable:
            return BattleMessages.failed()
        
        user.ability = target_ability
        target.ability = user_ability
        
        user.volatile["skill_swap_ability"] = target_ability
        target.volatile["skill_swap_ability"] = user_ability
        
        return BattleMessages.ability_swapped(user.display_name, user_ability, target.display_name, target_ability)
    
    def _handle_imprison(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("imprison"):
            return BattleMessages.failed()
        
        user.volatile["imprison"] = True
        
        if hasattr(user, 'moves'):
            user.volatile["imprison_moves"] = [m.get('id') for m in user.moves]
        
        return BattleMessages.imprisoned(target.display_name)
    
    def _handle_refresh(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        status_name = user.status.get("name")
        
        if not status_name or status_name not in ["burn", "paralysis", "poison", "toxic"]:
            return BattleMessages.failed()
        
        cured_status = status_name
        user.status = {"name": None, "counter": 0}
        user.volatile["refreshed"] = True
        
        return BattleMessages.status_cured(user.display_name, cured_status)
    
    def _handle_grudge(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["grudge"] = True
        user.volatile["grudge_active"] = True
        
        return BattleMessages.grudge_set(user.display_name)
    
    def _handle_snatch(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        user.volatile["snatch"] = True
        user.volatile["snatch_turns"] = 1
        
        return f"   └─ 🎯 {user.display_name} está esperando para roubar movimentos!"
    
    def _handle_camouflage(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        terrain = effect.get("terrain", "normal")
        
        terrain_types = {
            "normal": "normal",
            "grass": "grass",
            "water": "water",
            "electric": "electric",
            "psychic": "psychic",
            "ice": "ice",
            "cave": "rock",
            "sand": "ground"
        }
        
        new_type = terrain_types.get(terrain, "normal")
        
        if new_type in user.types:
            return BattleMessages.failed()
        
        user.volatile["original_types"] = user.types.copy()
        user.types = [new_type]
        user.volatile["camouflage_type"] = new_type
        
        return BattleMessages.type_changed(user.display_name, new_type)
    
    def _handle_mud_sport(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("mud_sport"):
            return BattleMessages.failed()
        
        user.volatile["mud_sport"] = True
        user.volatile["field_mud_sport"] = effect.get("turns", 5)
        
        return f"   └─ ⚡ Dano elétrico foi reduzido no campo!"
    
    def _handle_water_sport(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("water_sport"):
            return BattleMessages.failed()
        
        user.volatile["water_sport"] = True
        user.volatile["field_water_sport"] = effect.get("turns", 5)
        
        return f"   └─ 🔥 Dano de fogo foi reduzido no campo!"
    
    def _handle_trick_room(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        current_state = user.volatile.get("trick_room", False)
        turns = effect.get("turns", 5)
        
        user.volatile["trick_room"] = not current_state
        user.volatile["trick_room_turns"] = turns
        
        if user.volatile["trick_room"]:
            return BattleMessages.trick_room_set(turns)
        else:
            return BattleMessages.trick_room_ended()
    
    def _handle_gravity(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if user.volatile.get("gravity", 0) > 0:
            return BattleMessages.failed()
        
        turns = effect.get("turns", 5)
        user.volatile["gravity"] = turns
        user.volatile["field_gravity"] = True
        
        target.volatile["magnet_rise"] = 0
        target.volatile["telekinesis"] = 0
        
        return BattleMessages.gravity_set(turns)
    
    def _handle_conversion2(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        last_move_type = target.volatile.get("last_move_type")
        
        if not last_move_type:
            return BattleMessages.failed()
        
        resistance_map = {
            "fire": "water",
            "water": "grass",
            "grass": "fire",
            "electric": "ground",
            "normal": "rock",
            "fighting": "psychic",
            "flying": "electric",
            "poison": "psychic",
            "ground": "water",
            "rock": "water",
            "bug": "fire",
            "ghost": "dark",
            "steel": "fire",
            "psychic": "dark",
            "ice": "fire",
            "dragon": "ice",
            "dark": "fighting",
            "fairy": "steel"
        }
        
        new_type = resistance_map.get(last_move_type, "normal")
        
        user.volatile["original_types"] = user.types.copy()
        user.types = [new_type]
        user.volatile["conversion2_type"] = new_type
        
        return BattleMessages.type_changed(user.display_name, new_type)
    
    def _handle_psych_up(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        has_changes = False
        
        for stat in ["atk", "def", "sp_atk", "sp_def", "speed", "accuracy", "evasion"]:
            if target.stages.get(stat, 0) != 0:
                has_changes = True
                user.stages[stat] = target.stages[stat]
        
        if not has_changes:
            return BattleMessages.failed()
        
        user.volatile["psych_up_used"] = True
        
        return f"   └─ 🧠 {user.display_name} copiou as mudanças de stats de {target.display_name}!"
    
    def _handle_foresight(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        if target.volatile.get("foresight"):
            return BattleMessages.failed()
        
        target.volatile["foresight"] = True
        
        if target.stages.get("evasion", 0) > 0:
            target.stages["evasion"] = 0
        
        target.volatile["identified"] = True
        
        return BattleMessages.identified(target.display_name)

    def _handle_nothing(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage: int, move_data: Optional[MoveData] = None) -> str:
        return f" :face_with_raised_eyebrow: └─ {user.display_name} fez.... nada?!"
