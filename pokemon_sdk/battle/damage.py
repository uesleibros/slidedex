import random
from typing import Dict, Any, Tuple, Optional
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
        
        if effect_data.get("ohko"):
            return defender.current_hp, 1.0, False
        
        if effect_data.get("psywave"):
            damage = int(attacker.level * random.uniform(0.5, 1.5))
            return max(1, damage), 1.0, False
        
        if effect_data.get("super_fang"):
            return max(1, defender.current_hp // 2), 1.0, False
        
        if effect_data.get("endeavor"):
            return 0, 1.0, False
        
        if effect_data.get("spit_up"):
            stockpile = attacker.volatile.get("stockpile", 0)
            if stockpile == 0:
                return 0, 1.0, False
            power = 100 * stockpile
        else:
            power = move_data.power
        
        if power <= 0:
            return 0, 1.0, False
        
        power = self._modify_power(power, attacker, defender, move_data, effect_data)
        
        is_crit = self._calculate_crit(attacker, defender, move_data, effect_data)
        attack_stat, defense_stat = self._get_stats(attacker, defender, move_data, effect_data, is_crit)
        
        base_damage = self._base_damage(attacker.level, power, attack_stat, defense_stat)
        
        is_struggle = move_data.name.lower() == "struggle"
        type_mult = 1.0 if is_struggle else _type_mult(move_data.type_name, defender.types)
        
        if type_mult == 0.0:
            if defender.volatile.get("foresight") or defender.volatile.get("identified") or defender.volatile.get("miracle_eye"):
                if "ghost" in defender.types and move_data.type_name.lower() in ["normal", "fighting"]:
                    type_mult = 1.0
                else:
                    return 0, 0.0, False
            else:
                return 0, 0.0, False
        
        stab = self._calculate_stab(attacker, move_data, is_struggle)
        weather_mult = self._calculate_weather_mult(attacker, defender, move_data)
        other_mult = self._calculate_other_multipliers(attacker, defender, move_data, effect_data)
        
        random_mult = random.uniform(BattleConstants.DAMAGE_ROLL_MIN, BattleConstants.DAMAGE_ROLL_MAX)
        
        crit_mult = BattleConstants.CRIT_DAMAGE_MULT if is_crit else 1.0
        
        final_damage = int(
            base_damage * 
            stab * 
            type_mult * 
            weather_mult *
            other_mult *
            random_mult * 
            crit_mult
        )
        
        return max(1, final_damage), type_mult, is_crit
    
    def _get_stats(
        self, 
        attacker: BattlePokemon, 
        defender: BattlePokemon, 
        move_data: MoveData,
        effect_data: Dict[str, Any],
        is_crit: bool
    ) -> Tuple[int, int]:
        
        if move_data.dmg_class == "special":
            if is_crit:
                attack = attacker.eff_stat("sp_atk") if attacker.stages.get("sp_atk", 0) >= 0 else attacker.stats["special-attack"]
            else:
                attack = attacker.eff_stat("sp_atk")

            if is_crit:
                defense = defender.eff_stat("sp_def") if defender.stages.get("sp_def", 0) <= 0 else defender.stats["special-defense"]
            else:
                defense = defender.eff_stat("sp_def")
            
            if defender.volatile.get("light_screen", 0) > 0:
                defense = int(defense * BattleConstants.SCREEN_DEF_MULT)
            
            if defender.volatile.get("held_item") == "assault_vest":
                defense = int(defense * 1.5)
        
        else:
            if is_crit:
                attack = attacker.eff_stat("atk") if attacker.stages.get("atk", 0) >= 0 else attacker.stats["attack"]
            else:
                attack = attacker.eff_stat("atk")
            
            if attacker.status["name"] == "burn":
                ability = attacker.get_effective_ability()
                if ability != "guts":
                    attack = int(attack * BattleConstants.BURN_ATK_MULT)
            
            if is_crit:
                defense = defender.eff_stat("def") if defender.stages.get("def", 0) <= 0 else defender.stats.get("defense", defender.stats.get("def"))
            else:
                defense = defender.eff_stat("def")
            
            if defender.volatile.get("reflect", 0) > 0:
                defense = int(defense * BattleConstants.SCREEN_DEF_MULT)
            
            if self.weather.get("type") == "sandstorm" and "rock" in defender.types:
                defense = int(defense * 1.5)
        
        return attack, defense
    
    def _modify_power(
        self, 
        power: int, 
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_data: MoveData,
        effect_data: Dict[str, Any]
    ) -> int:
        modified_power = power
        move_type = move_data.type_name.lower()
        move_id = move_data.id.lower()
        
        if effect_data.get("facade") and attacker.status["name"] in ["burn", "poison", "toxic", "paralysis"]:
            modified_power *= 2
        
        if effect_data.get("brine") and defender.current_hp <= defender.stats["hp"] // 2:
            modified_power *= 2
        
        if effect_data.get("venoshock") and defender.status["name"] in ["poison", "toxic"]:
            modified_power *= 2
        
        if effect_data.get("smelling_salts") and defender.status["name"] == "paralysis":
            modified_power *= 2
        
        if effect_data.get("wake_up_slap") and defender.status["name"] == "sleep":
            modified_power *= 2
        
        if move_id == "acrobatics" and not attacker.volatile.get("held_item"):
            modified_power *= 2
        
        if move_id == "hex" and defender.status["name"]:
            modified_power *= 2
        
        if move_id in ["revenge", "avalanche"] and attacker.volatile.get("last_damage_taken", 0) > 0:
            modified_power *= 2
        
        if move_id == "assurance" and defender.volatile.get("last_damage_taken", 0) > 0:
            modified_power *= 2
        
        if move_id == "payback" and defender.volatile.get("moved_this_turn"):
            modified_power *= 2
        
        if move_id in ["solar_beam", "solar_blade"]:
            weather_type = self.weather.get("type")
            if weather_type and weather_type != "sun":
                modified_power //= 2
        
        if move_id == "weather_ball" and self.weather.get("type"):
            modified_power *= 2
        
        if move_id == "terrain_pulse" and attacker.volatile.get("terrain"):
            modified_power *= 2
        
        if move_id == "rising_voltage" and attacker.volatile.get("terrain") == "electric":
            modified_power *= 2
        
        if move_id in ["gust", "twister"] and defender.volatile.get("two_turn_move") in ["fly", "bounce", "sky_drop"]:
            modified_power *= 2
        
        if move_id in ["earthquake", "magnitude"] and defender.volatile.get("two_turn_move") == "dig":
            modified_power *= 2
        
        if move_id in ["surf", "whirlpool"] and defender.volatile.get("two_turn_move") == "dive":
            modified_power *= 2
        
        stomp_moves = ["stomp", "body_slam", "dragon_rush", "flying_press", "heat_crash", "heavy_slam", "steamroller"]
        if move_id in stomp_moves and (defender.volatile.get("minimized") or defender.volatile.get("minimize_used")):
            modified_power *= 2
        
        if move_id == "rollout":
            count = attacker.volatile.get("rollout_count", 0)
            modified_power *= (2 ** count)
            if attacker.volatile.get("defense_curl_used"):
                modified_power *= 2
        
        if move_id == "ice_ball":
            count = attacker.volatile.get("ice_ball_count", 0)
            modified_power *= (2 ** count)
            if attacker.volatile.get("defense_curl_used"):
                modified_power *= 2
        
        if move_id == "fury_cutter":
            count = attacker.volatile.get("fury_cutter_count", 0)
            modified_power = min(160, power * (2 ** count))
        
        if move_id == "echoed_voice":
            count = attacker.volatile.get("echoed_voice_count", 0)
            modified_power = min(200, power + (40 * count))
        
        if attacker.volatile.get("charge") and move_type == "electric":
            modified_power *= 2
        
        if attacker.volatile.get("helping_hand"):
            modified_power = int(modified_power * 1.5)
        
        if effect_data.get("me_first"):
            modified_power = int(modified_power * 1.5)
        
        if attacker.volatile.get("flash_fire") and move_type == "fire":
            modified_power = int(modified_power * 1.5)
        
        ability = attacker.get_effective_ability()
        
        if ability == "technician" and power <= 60:
            modified_power = int(modified_power * 1.5)
        
        punch_moves = ["fire_punch", "ice_punch", "thunder_punch", "mega_punch", "meteor_mash", 
                       "hammer_arm", "drain_punch", "focus_punch", "dynamic_punch", "mach_punch",
                       "bullet_punch", "shadow_punch", "sky_uppercut", "dizzy_punch"]
        if ability == "iron_fist" and move_id in punch_moves:
            modified_power = int(modified_power * 1.2)
        
        if ability == "reckless" and effect_data.get("recoil"):
            modified_power = int(modified_power * 1.2)
        
        if ability == "sheer_force" and effect_data.get("effects"):
            modified_power = int(modified_power * 1.3)
        
        if ability == "rivalry" and hasattr(attacker, 'gender') and hasattr(defender, 'gender'):
            if attacker.gender and defender.gender:
                if attacker.gender == defender.gender:
                    modified_power = int(modified_power * 1.25)
                else:
                    modified_power = int(modified_power * 0.75)
        
        type_ability_map = {
            "overgrow": ("grass", 1.5),
            "blaze": ("fire", 1.5),
            "torrent": ("water", 1.5),
            "swarm": ("bug", 1.5),
            "chlorophyll": ("grass", 1.5) if self.weather.get("type") == "sun" else ("grass", 1.0),
        }
        
        if ability in type_ability_map:
            boost_type, multiplier = type_ability_map[ability]
            if move_type == boost_type:
                if ability in ["overgrow", "blaze", "torrent", "swarm"]:
                    if attacker.current_hp <= attacker.stats["hp"] // 3:
                        modified_power = int(modified_power * multiplier)
                else:
                    modified_power = int(modified_power * multiplier)
        
        return max(1, modified_power)
    
    def _base_damage(self, level: int, power: int, attack: int, defense: int) -> float:
        return (((2 * level / 5) + 2) * power * (attack / max(1, defense))) / 50 + 2
    
    def _calculate_stab(self, attacker: BattlePokemon, move_data: MoveData, is_struggle: bool) -> float:
        if is_struggle:
            return 1.0
        
        move_type = move_data.type_name.lower()
        types = attacker.get_effective_types()
        
        if move_type in types:
            ability = attacker.get_effective_ability()
            if ability == "adaptability":
                return 2.0
            return BattleConstants.STAB_MULT
        
        return 1.0
    
    def _calculate_crit(
        self, 
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_data: MoveData,
        effect_data: Dict[str, Any]
    ) -> bool:
        is_struggle = move_data.name.lower() == "struggle"
        
        if is_struggle:
            return False
        
        if effect_data.get("always_crit"):
            return True
        
        defender_ability = defender.get_effective_ability()
        if defender_ability in ["battle_armor", "shell_armor"]:
            return False
        
        crit_ratio = effect_data.get("critical_hit_ratio", 0)
        
        if attacker.volatile.get("focus_energy"):
            crit_ratio += 2
        
        if attacker.get_effective_ability() == "super_luck":
            crit_ratio += 1
        
        item = attacker.volatile.get("held_item", "")
        if item in ["scope_lens", "razor_claw"]:
            crit_ratio += 1
        
        if item == "lucky_punch" and attacker.species_id == 113:
            crit_ratio += 2
        
        if item == "stick" and attacker.species_id == 83:
            crit_ratio += 2
    
        if crit_ratio <= 0:
            crit_chance = BattleConstants.CRIT_BASE_CHANCE
        elif crit_ratio == 1:
            crit_chance = 1/8
        elif crit_ratio == 2:
            crit_chance = 1/2
        else:
            crit_chance = 1.0
        
        return random.random() < crit_chance
    
    def _calculate_weather_mult(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_data: MoveData
    ) -> float:
        weather_type = self.weather.get("type") or attacker.volatile.get("weather")
        
        if not weather_type or self.weather.get("turns", 0) <= 0:
            return 1.0
        
        move_type = move_data.type_name.lower()
        
        attacker_ability = attacker.get_effective_ability()
        defender_ability = defender.get_effective_ability()
        
        if attacker_ability in ["cloud_nine", "air_lock"] or defender_ability in ["cloud_nine", "air_lock"]:
            return 1.0
        
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
    
    def _calculate_other_multipliers(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_data: MoveData,
        effect_data: Dict[str, Any]
    ) -> float:
        multiplier = 1.0
        move_type = move_data.type_name.lower()
        
        if attacker.volatile.get("field_mud_sport", 0) > 0 or defender.volatile.get("field_mud_sport", 0) > 0:
            if move_type == "electric":
                multiplier *= 0.33
        
        if attacker.volatile.get("field_water_sport", 0) > 0 or defender.volatile.get("field_water_sport", 0) > 0:
            if move_type == "fire":
                multiplier *= 0.33
        
        defender_ability = defender.get_effective_ability()
        
        if defender_ability == "thick_fat" and move_type in ["fire", "ice"]:
            multiplier *= 0.5
        
        if defender_ability == "heatproof" and move_type == "fire":
            multiplier *= 0.5
        
        if defender_ability == "dry_skin" and move_type == "fire":
            multiplier *= 1.25
        
        if defender_ability in ["filter", "solid_rock"]:
            type_mult = _type_mult(move_data.type_name, defender.types)
            if type_mult > 1.0:
                multiplier *= 0.75
        
        if defender_ability in ["multiscale", "shadow_shield"]:
            if defender.current_hp == defender.stats["hp"]:
                multiplier *= 0.5
        
        if defender_ability == "fluffy":
            if effect_data.get("makes_contact"):
                multiplier *= 0.5
            if move_type == "fire":
                multiplier *= 2.0
        
        if defender_ability == "punk_rock" and effect_data.get("sound_move"):
            multiplier *= 0.5
        
        if defender_ability == "ice_scales" and move_data.dmg_class == "special":
            multiplier *= 0.5
        
        attacker_ability = attacker.get_effective_ability()
        
        if attacker_ability == "tinted_lens":
            type_mult = _type_mult(move_data.type_name, defender.types)
            if type_mult < 1.0:
                multiplier *= 2.0
        
        if attacker_ability == "neuroforce":
            type_mult = _type_mult(move_data.type_name, defender.types)
            if type_mult > 1.0:
                multiplier *= 1.25
        
        if attacker_ability == "tough_claws" and effect_data.get("makes_contact"):
            multiplier *= 1.3
        
        bite_moves = ["bite", "crunch", "fire_fang", "ice_fang", "thunder_fang", "poison_fang", 
                      "psychic_fangs", "fishious_rend", "hyper_fang", "jaw_lock"]
        if attacker_ability == "strong_jaw" and move_data.id.lower() in bite_moves:
            multiplier *= 1.5
        
        pulse_moves = ["water_pulse", "dragon_pulse", "aura_sphere", "dark_pulse", "terrain_pulse"]
        if attacker_ability == "mega_launcher" and move_data.id.lower() in pulse_moves:
            multiplier *= 1.5
        
        if attacker_ability == "punk_rock" and effect_data.get("sound_move"):
            multiplier *= 1.3
        
        return multiplier
