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
            "self_destruct": self._handle_self_destruct
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
        
        actual_change, old_value = target.modify_stat_stage(stat, stages)
        
        if actual_change == 0:
            if old_value == BattleConstants.MAX_STAT_STAGE and stages > 0:
                return [BattleMessages.stat_maxed(target.display_name, stat, True)]
            elif old_value == BattleConstants.MIN_STAT_STAGE and stages < 0:
                return [BattleMessages.stat_maxed(target.display_name, stat, False)]
            return None
        
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
        return f"   └─ 🌿 {user.display_name} criou raízes! (Cura 1/16 HP por turno)"
    
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
