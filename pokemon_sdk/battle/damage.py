import random
from typing import Dict, Any, Tuple
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .helpers import _type_mult, MoveData

class DamageCalculator:
    
    def __init__(self, weather: Dict[str, Any]):
        self.weather = weather
    
    async def calculate(
        self, 
        attacker: BattlePokemon, 
        defender: BattlePokemon, 
        move_data: MoveData, 
        effect_data: Dict[str, Any]
    ) -> Tuple[int, float, bool]:
        if move_data.power <= 0 and not effect_data.get("damage", False):
            return 0, 1.0, False
        
        if effect_data.get("fixed_damage"):
            return effect_data["fixed_damage"], 1.0, False
        
        if effect_data.get("level_damage"):
            return attacker.level, 1.0, False
        
        power = move_data.power
        if power <= 0:
            return 0, 1.0, False
        
        attack_stat, defense_stat = self._get_stats(attacker, defender, move_data, effect_data)
        power = self._modify_power(power, attacker, move_data, effect_data)
        
        base_damage = self._base_damage(attacker.level, power, attack_stat, defense_stat)
        
        is_struggle = move_data.name.lower() == "struggle"
        type_mult = 1.0 if is_struggle else _type_mult(move_data.type_name, defender.types)
        
        if type_mult == 0.0:
            return 0, 0.0, False
        
        stab = self._calculate_stab(attacker, move_data, is_struggle)
        is_crit = self._calculate_crit(attacker, effect_data, is_struggle)
        weather_mult = self._calculate_weather_mult(move_data)
        
        final_damage = int(
            base_damage * 
            stab * 
            type_mult * 
            weather_mult * 
            random.uniform(BattleConstants.DAMAGE_ROLL_MIN, BattleConstants.DAMAGE_ROLL_MAX) * 
            (BattleConstants.CRIT_DAMAGE_MULT if is_crit else 1.0)
        )
        
        return max(1, final_damage), type_mult, is_crit
    
    def _get_stats(
        self, 
        attacker: BattlePokemon, 
        defender: BattlePokemon, 
        move_data: MoveData,
        effect_data: Dict[str, Any]
    ) -> Tuple[int, int]:
        if move_data.dmg_class == "special":
            attack = attacker.eff_stat("sp_atk")
            defense = defender.eff_stat("sp_def")
            
            if defender.volatile.get("light_screen", 0) > 0:
                defense = int(defense * BattleConstants.SCREEN_DEF_MULT)
        else:
            attack = attacker.eff_stat("atk")
            defense = defender.eff_stat("def")
            
            if attacker.status["name"] == "burn":
                attack = int(attack * BattleConstants.BURN_ATK_MULT)
            
            if defender.volatile.get("reflect", 0) > 0:
                defense = int(defense * BattleConstants.SCREEN_DEF_MULT)
        
        return attack, defense
    
    def _modify_power(
        self, 
        power: int, 
        attacker: BattlePokemon, 
        move_data: MoveData,
        effect_data: Dict[str, Any]
    ) -> int:
        if effect_data.get("facade") and attacker.status["name"] in ["burn", "poison", "toxic", "paralysis"]:
            power *= 2
        
        return power
    
    def _base_damage(self, level: int, power: int, attack: int, defense: int) -> float:
        return (((2 * level / 5) + 2) * power * (attack / max(1, defense))) / 50 + 2
    
    def _calculate_stab(self, attacker: BattlePokemon, move_data: MoveData, is_struggle: bool) -> float:
        if is_struggle:
            return 1.0
        return BattleConstants.STAB_MULT if move_data.type_name.lower() in attacker.types else 1.0
    
    def _calculate_crit(self, attacker: BattlePokemon, effect_data: Dict[str, Any], is_struggle: bool) -> bool:
        if is_struggle:
            return False
        
        crit_ratio = effect_data.get("critical_hit_ratio", 0)
        if attacker.volatile.get("focus_energy"):
            crit_ratio += 1
        
        crit_chance = BattleConstants.CRIT_BASE_CHANCE * (2 ** crit_ratio) if crit_ratio > 0 else BattleConstants.CRIT_BASE_CHANCE
        return random.random() < crit_chance
    
    def _calculate_weather_mult(self, move_data: MoveData) -> float:
        if not self.weather.get("type") or self.weather.get("turns", 0) <= 0:
            return 1.0
        
        weather_type = self.weather["type"]
        move_type = move_data.type_name.lower()
        
        if weather_type == "sun":
            if move_type == "fire":
                return BattleConstants.WEATHER_BOOST_MULT
            elif move_type == "water":
                return BattleConstants.WEATHER_NERF_MULT
        elif weather_type == "rain":
            if move_type == "water":
                return BattleConstants.WEATHER_BOOST_MULT
            elif move_type == "fire":
                return BattleConstants.WEATHER_NERF_MULT
        
        return 1.0
