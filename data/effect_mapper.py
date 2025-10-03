effect_mapper: dict = {
    "Inflicts regular damage with no additional effect.": {
        "damage": True,
        "effects": []
    },
    "Has an increased chance for a critical hit.": {
        "damage": True,
        "critical_hit_ratio": 1,
        "effects": []
    },
    "Hits 2-5 times in one turn.": {
        "damage": True,
        "multi_hit": {"min": 2, "max": 5},
        "effects": []
    },
    "Scatters money on the ground worth five times the user's level.": {
        "damage": True,
        "effects": [{"type": "pay_day", "multiplier": 5}]
    },
    "Has a 10% chance to burn the target.": {
        "damage": True,
        "effects": [{"type": "burn", "chance": 10, "target": "opponent"}]
    },
    "Has a 10% chance to freeze the target.": {
        "damage": True,
        "effects": [{"type": "freeze", "chance": 10, "target": "opponent"}]
    },
    "Has a 10% chance to paralyze the target.": {
        "damage": True,
        "effects": [{"type": "paralysis", "chance": 10, "target": "opponent"}]
    },
    "Causes a one-hit KO.": {
        "damage": False,
        "ohko": True,
        "effects": []
    },
    "Requires a turn to charge before attacking.": {
        "damage": True,
        "charge_turns": 1,
        "effects": []
    },
    "Raises the user's Attack by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": 2, "target": "self"}]
    },
    "Inflicts regular damage and can hit Pokémon in the air.": {
        "damage": True,
        "can_hit_flying": True,
        "effects": []
    },
    "Immediately ends wild battles.  Forces trainers to switch Pokémon.": {
        "damage": True,
        "effects": [{"type": "force_switch", "target": "opponent"}]
    },
    "User flies high into the air, dodging all attacks, and hits next turn.": {
        "damage": True,
        "semi_invulnerable_turns": 1,
        "effects": []
    },
    "Prevents the target from fleeing and inflicts damage for 2-5 turns.": {
        "damage": True,
        "effects": [{"type": "bind", "min_turns": 2, "max_turns": 5, "target": "opponent"}]
    },
    "Has a 30% chance to make the target flinch.": {
        "damage": True,
        "effects": [{"type": "flinch", "chance": 30, "target": "opponent"}]
    },
    "Hits twice in one turn.": {
        "damage": True,
        "multi_hit": {"min": 2, "max": 2},
        "effects": []
    },
    "If the user misses, it takes half the damage it would have inflicted in recoil.": {
        "damage": True,
        "effects": [{"type": "crash_damage", "damage_ratio": 0.5}]
    },
    "Lowers the target's accuracy by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "accuracy", "stages": -1, "target": "opponent"}]
    },
    "Has a 30% chance to paralyze the target.": {
        "damage": True,
        "effects": [{"type": "paralysis", "chance": 30, "target": "opponent"}]
    },
    "User receives 1/4 the damage it inflicts in recoil.": {
        "damage": True,
        "recoil": 0.25,
        "effects": []
    },
    "Hits every turn for 2-3 turns, then confuses the user.": {
        "damage": True,
        "rampage": {"min_turns": 2, "max_turns": 3},
        "effects": [{"type": "confusion", "target": "self", "after_rampage": True}]
    },
    "User receives 1/3 the damage inflicted in recoil.": {
        "damage": True,
        "recoil": 0.33,
        "effects": []
    },
    "Lowers the target's Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": -1, "target": "opponent"}]
    },
    "Has a 30% chance to poison the target.": {
        "damage": True,
        "effects": [{"type": "poison", "chance": 30, "target": "opponent"}]
    },
    "Hits twice in the same turn.  Has a 20% chance to poison the target.": {
        "damage": True,
        "multi_hit": {"min": 2, "max": 2},
        "effects": [{"type": "poison", "chance": 20, "target": "opponent"}]
    },
    "Lowers the target's Attack by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": -1, "target": "opponent"}]
    },
    "Puts the target to sleep.": {
        "damage": False,
        "effects": [{"type": "sleep", "chance": 100, "target": "opponent"}]
    },
    "Confuses the target.": {
        "damage": False,
        "effects": [{"type": "confusion", "chance": 100, "target": "opponent"}]
    },
    "Inflicts 20 points of damage.": {
        "damage": True,
        "fixed_damage": 20,
        "effects": []
    },
    "Disables the target's last used move for 1-8 turns.": {
        "damage": False,
        "effects": [{"type": "disable", "min_turns": 1, "max_turns": 8, "target": "opponent"}]
    },
    "Has a 10% chance to lower the target's Special Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "special_defense", "stages": -1, "chance": 10, "target": "opponent"}]
    },
    "Has a 10% chance to burn the target.": {
        "damage": True,
        "effects": [{"type": "burn", "chance": 10, "target": "opponent"}]
    },
    "Protects the user's stats from being changed by enemy moves.": {
        "damage": False,
        "effects": [{"type": "mist", "target": "self"}]
    },
    "Inflicts regular damage and can hit Dive users.": {
        "damage": True,
        "can_hit_dive": True,
        "effects": []
    },
    "Has a 10% chance to confuse the target.": {
        "damage": True,
        "effects": [{"type": "confusion", "chance": 10, "target": "opponent"}]
    },
    "Has a 10% chance to lower the target's Speed by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "speed", "stages": -1, "chance": 10, "target": "opponent"}]
    },
    "Has a 10% chance to lower the target's Attack by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": -1, "chance": 10, "target": "opponent"}]
    },
    "User foregoes its next turn to recharge.": {
        "damage": True,
        "recharge_turns": 1,
        "effects": []
    },
    "Inflicts more damage to heavier targets, with a maximum of 120 power.": {
        "damage": True,
        "weight_based": True,
        "max_power": 120,
        "effects": []
    },
    "Inflicts twice the damage the user received from the last physical hit it took.": {
        "damage": True,
        "counter": "physical",
        "multiplier": 2,
        "effects": []
    },
    "Inflicts damage equal to the user's level.": {
        "damage": True,
        "level_damage": True,
        "effects": []
    },
    "Drains half the damage inflicted to heal the user.": {
        "damage": True,
        "drain": 0.5,
        "effects": []
    },
    "Seeds the target, stealing HP from it every turn.": {
        "damage": False,
        "effects": [{"type": "leech_seed", "target": "opponent"}]
    },
    "Raises the user's Attack and Special Attack by one stage.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": 1, "target": "self"},
            {"type": "stat_change", "stat": "special_attack", "stages": 1, "target": "self"}
        ]
    },
    "Poisons the target.": {
        "damage": False,
        "effects": [{"type": "poison", "chance": 100, "target": "opponent"}]
    },
    "Paralyzes the target.": {
        "damage": False,
        "effects": [{"type": "paralysis", "chance": 100, "target": "opponent"}]
    },
    "Lowers the target's Speed by two stages.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "speed", "stages": -2, "target": "opponent"}]
    },
    "Inflicts 40 points of damage.": {
        "damage": True,
        "fixed_damage": 40,
        "effects": []
    },
    "Inflicts regular damage and can hit Dig users.": {
        "damage": True,
        "can_hit_dig": True,
        "effects": []
    },
    "User digs underground, dodging all attacks, and hits next turn.": {
        "damage": True,
        "semi_invulnerable_turns": 1,
        "effects": []
    },
    "Badly poisons the target, inflicting more damage every turn.": {
        "damage": False,
        "effects": [{"type": "toxic", "chance": 100, "target": "opponent"}]
    },
    "Raises the user's Attack by one stage.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": 1, "target": "self"}]
    },
    "Raises the user's Speed by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "speed", "stages": 2, "target": "self"}]
    },
    "If the user is hit after using this move, its Attack rises by one stage.": {
        "damage": False,
        "effects": [{"type": "rage", "stat": "attack", "stages": 1, "target": "self"}]
    },
    "Immediately ends wild battles.  No effect otherwise.": {
        "damage": False,
        "effects": [{"type": "teleport"}]
    },
    "Copies the target's last used move.": {
        "damage": False,
        "effects": [{"type": "mimic", "target": "opponent"}]
    },
    "Lowers the target's Defense by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": -2, "target": "opponent"}]
    },
    "Raises the user's evasion by one stage.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "evasion", "stages": 1, "target": "self"}]
    },
    "Heals the user by half its max HP.": {
        "damage": False,
        "effects": [{"type": "heal", "amount": 0.5, "target": "self"}]
    },
    "Raises the user's Defense by one stage.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": 1, "target": "self"}]
    },
    "Raises user's Defense by one stage.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": 1, "target": "self"}]
    },
    "Raises the user's evasion by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "evasion", "stages": 2, "target": "self"}]
    },
    "Raises the user's Defense by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": 2, "target": "self"}]
    },
    "Reduces damage from special attacks by 50% for five turns.": {
        "damage": False,
        "effects": [{"type": "light_screen", "turns": 5}]
    },
    "Resets all Pokémon's stats, accuracy, and evasion.": {
        "damage": False,
        "effects": [{"type": "haze"}]
    },
    "Reduces damage from physical attacks by half.": {
        "damage": False,
        "effects": [{"type": "reflect", "turns": 5}]
    },
    "Increases the user's chance to score a critical hit.": {
        "damage": False,
        "effects": [{"type": "focus_energy", "target": "self"}]
    },
    "User waits for two turns, then hits back for twice the damage it took.": {
        "damage": True,
        "bide_turns": 2,
        "multiplier": 2,
        "effects": []
    },
    "Randomly selects and uses any move in the game.": {
        "damage": False,
        "effects": [{"type": "metronome"}]
    },
    "Uses the target's last used move.": {
        "damage": False,
        "effects": [{"type": "mirror_move", "target": "opponent"}]
    },
    "User faints.": {
        "damage": True,
        "effects": [{"type": "self_destruct", "target": "self"}]
    },
    "Has a 40% chance to poison the target.": {
        "damage": True,
        "effects": [{"type": "poison", "chance": 40, "target": "opponent"}]
    },
    "Has a 10% chance to make the target flinch.": {
        "damage": True,
        "effects": [{"type": "flinch", "chance": 10, "target": "opponent"}]
    },
    "Has a 20% chance to make the target flinch.": {
        "damage": True,
        "effects": [{"type": "flinch", "chance": 20, "target": "opponent"}]
    },
    "Never misses.": {
        "damage": True,
        "bypass_accuracy": True,
        "effects": []
    },
    "Raises the user's Defense by one stage.  User charges for one turn before attacking.": {
        "damage": True,
        "charge_turns": 1,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": 1, "target": "self"}]
    },
    "Raises the user's Special Defense by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "special_defense", "stages": 2, "target": "self"}]
    },
    "Only works on sleeping Pokémon.  Drains half the damage inflicted to heal the user.": {
        "damage": True,
        "drain": 0.5,
        "requires_sleeping_target": True,
        "effects": []
    },
    "User charges for one turn before attacking.  Has a 30% chance to make the target flinch.": {
        "damage": True,
        "charge_turns": 1,
        "effects": [{"type": "flinch", "chance": 30, "target": "opponent"}]
    },
    "User becomes a copy of the target until it leaves battle.": {
        "damage": False,
        "effects": [{"type": "transform", "target": "opponent"}]
    },
    "Has a 20% chance to confuse the target.": {
        "damage": True,
        "effects": [{"type": "confusion", "chance": 20, "target": "opponent"}]
    },
    "Inflicts damage between 50% and 150% of the user's level.": {
        "damage": True,
        "variable_damage": {"min": 0.5, "max": 1.5},
        "effects": []
    },
    "Does nothing.": {
        "damage": False,
        "effects": [{"type": "nothing"}]
    },
    "User sleeps for two turns, completely healing itself.": {
        "damage": False,
        "effects": [{"type": "rest", "sleep_turns": 2, "target": "self"}]
    },
    "User's type changes to the type of one of its moves at random.": {
        "damage": False,
        "effects": [{"type": "conversion", "target": "self"}]
    },
    "Has a 20% chance to burn, freeze, or paralyze the target.": {
        "damage": True,
        "effects": [{"type": "tri_attack", "chance": 20, "target": "opponent"}]
    },
    "Inflicts damage equal to half the target's HP.": {
        "damage": True,
        "half_hp_damage": True,
        "effects": []
    },
    "Transfers 1/4 of the user's max HP into a doll, protecting the user from further damage or status changes until it breaks.": {
        "damage": False,
        "effects": [{"type": "substitute", "hp_cost": 0.25, "target": "self"}]
    },
    "User takes 1/4 its max HP in recoil.": {
        "damage": True,
        "recoil": 0.25,
        "effects": []
    },
    "Permanently becomes the target's last used move.": {
        "damage": False,
        "effects": [{"type": "sketch", "target": "opponent"}]
    },
    "Hits three times, increasing power by 100% with each successful hit.": {
        "damage": True,
        "triple_kick": True,
        "effects": []
    },
    "Takes the target's item.": {
        "damage": True,
        "effects": [{"type": "steal_item", "target": "opponent"}]
    },
    "Prevents the target from leaving battle.": {
        "damage": False,
        "effects": [{"type": "trap", "target": "opponent"}]
    },
    "Ensures that the user's next move will hit the target.": {
        "damage": False,
        "effects": [{"type": "mind_reader", "target": "self"}]
    },
    "Target loses 1/4 its max HP every turn as long as it's asleep.": {
        "damage": False,
        "effects": [{"type": "nightmare", "target": "opponent"}]
    },
    "Has a 10% chance to burn the target.  Lets frozen Pokémon thaw themselves.": {
        "damage": True,
        "thaws_user": True,
        "effects": [{"type": "burn", "chance": 10, "target": "opponent"}]
    },
    "Has a 30% chance to make the target flinch.  Only works if the user is sleeping.": {
        "damage": True,
        "requires_sleeping_user": True,
        "effects": [{"type": "flinch", "chance": 30, "target": "opponent"}]
    },
    "Ghosts pay half their max HP to hurt the target every turn.  Others decrease Speed but raise Attack and Defense.": {
        "damage": False,
        "effects": [{"type": "curse", "target": "varies"}]
    },
    "Inflicts more damage when the user has less HP remaining, with a maximum of 200 power.": {
        "damage": True,
        "reversal_based": True,
        "max_power": 200,
        "effects": []
    },
    "Changes the user's type to a random type either resistant or immune to the last move used against it.": {
        "damage": False,
        "effects": [{"type": "conversion2", "target": "self"}]
    },
    "Lowers the PP of the target's last used move by 4.": {
        "damage": False,
        "effects": [{"type": "spite", "pp_reduction": 4, "target": "opponent"}]
    },
    "Prevents any moves from hitting the user this turn.": {
        "damage": False,
        "effects": [{"type": "protect", "target": "self"}]
    },
    "User pays half its max HP to max out its Attack.": {
        "damage": False,
        "effects": [{"type": "belly_drum", "hp_cost": 0.5, "target": "self"}]
    },
    "Has a 100% chance to lower the target's accuracy by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "accuracy", "stages": -1, "chance": 100, "target": "opponent"}]
    },
    "Has a 50% chance to lower the target's accuracy by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "accuracy", "stages": -1, "chance": 50, "target": "opponent"}]
    },
    "Scatters Spikes, hurting opposing Pokémon that switch in.": {
        "damage": False,
        "effects": [{"type": "spikes", "target": "field"}]
    },
    "Has a 100% chance to paralyze the target.": {
        "damage": True,
        "effects": [{"type": "paralysis", "chance": 100, "target": "opponent"}]
    },
    "Forces the target to have no Evade, and allows it to be hit by Normal and Fighting moves even if it's a Ghost.": {
        "damage": False,
        "effects": [{"type": "foresight", "target": "opponent"}]
    },
    "If the user faints this turn, the target automatically will, too.": {
        "damage": False,
        "effects": [{"type": "destiny_bond", "target": "self"}]
    },
    "User and target both faint after three turns.": {
        "damage": False,
        "effects": [{"type": "perish_song", "turns": 3}]
    },
    "Has a 100% chance to lower the target's Speed by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "speed", "stages": -1, "chance": 100, "target": "opponent"}]
    },
    "Prevents the user's HP from lowering below 1 this turn.": {
        "damage": False,
        "effects": [{"type": "endure", "target": "self"}]
    },
    "Lowers the target's Attack by two stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": -2, "target": "opponent"}]
    },
    "Power doubles every turn this move is used in succession after the first, resetting after five turns.": {
        "damage": True,
        "rollout": True,
        "max_turns": 5,
        "effects": []
    },
    "Cannot lower the target's HP below 1.": {
        "damage": True,
        "false_swipe": True,
        "effects": []
    },
    "Raises the target's Attack by two stages and confuses the target.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": 2, "target": "opponent"},
            {"type": "confusion", "chance": 100, "target": "opponent"}
        ]
    },
    "Power doubles every turn this move is used in succession after the first, maxing out after five turns.": {
        "damage": True,
        "fury_cutter": True,
        "max_turns": 5,
        "effects": []
    },
    "Has a 10% chance to raise the user's Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": 1, "chance": 10, "target": "self"}]
    },
    "Target falls in love if it has the opposite gender, and has a 50% chance to refuse attacking the user.": {
        "damage": False,
        "effects": [{"type": "attract", "target": "opponent"}]
    },
    "Randomly uses one of the user's other three moves.  Only works if the user is sleeping.": {
        "damage": False,
        "requires_sleeping_user": True,
        "effects": [{"type": "sleep_talk"}]
    },
    "Cures the entire party of major status effects.": {
        "damage": False,
        "effects": [{"type": "heal_bell", "target": "party"}]
    },
    "Power increases with happiness, up to a maximum of 102.": {
        "damage": True,
        "happiness_based": True,
        "max_power": 102,
        "effects": []
    },
    "Randomly inflicts damage with power from 40 to 120 or heals the target for 1/4 its max HP.": {
        "damage": True,
        "present": True,
        "effects": []
    },
    "Power increases as happiness decreases, up to a maximum of 102.": {
        "damage": True,
        "frustration_based": True,
        "max_power": 102,
        "effects": []
    },
    "Protects the user's field from major status ailments and confusion for five turns.": {
        "damage": False,
        "effects": [{"type": "safeguard", "turns": 5, "target": "field"}]
    },
    "Sets the user's and targets's HP to the average of their current HP.": {
        "damage": False,
        "effects": [{"type": "pain_split", "target": "both"}]
    },
    "Has a 50% chance to burn the target.  Lets frozen Pokémon thaw themselves.": {
        "damage": True,
        "thaws_user": True,
        "effects": [{"type": "burn", "chance": 50, "target": "opponent"}]
    },
    "Power varies randomly from 10 to 150.": {
        "damage": True,
        "magnitude": True,
        "effects": []
    },
    "Has a 100% chance to confuse the target.": {
        "damage": True,
        "effects": [{"type": "confusion", "chance": 100, "target": "opponent"}]
    },
    "Allows the trainer to switch out the user and pass effects along to its replacement.": {
        "damage": False,
        "effects": [{"type": "baton_pass", "target": "self"}]
    },
    "Forces the target to repeat its last used move every turn for 2 to 6 turns.": {
        "damage": False,
        "effects": [{"type": "encore", "min_turns": 2, "max_turns": 6, "target": "opponent"}]
    },
    "Has double power against, and can hit, Pokémon attempting to switch out.": {
        "damage": True,
        "pursuit": True,
        "effects": []
    },
    "Frees the user from binding moves, removes Leech Seed, and blows away Spikes.": {
        "damage": False,
        "effects": [{"type": "rapid_spin", "target": "self"}]
    },
    "Lowers the target's evasion by one stage.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "evasion", "stages": -1, "target": "opponent"}]
    },
    "Has a 30% chance to lower the target's Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": -1, "chance": 30, "target": "opponent"}]
    },
    "Has a 10% chance to raise the user's Attack by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": 1, "chance": 10, "target": "self"}]
    },
    "Heals the user by half its max HP.  Affected by weather.": {
        "damage": False,
        "weather_dependent": True,
        "effects": [{"type": "heal", "amount": 0.5, "target": "self"}]
    },
    "Power and type depend upon user's IVs.  Power can range from 30 to 70.": {
        "damage": True,
        "hidden_power": True,
        "effects": []
    },
    "Changes the weather to rain for five turns.": {
        "damage": False,
        "effects": [{"type": "weather", "weather": "rain", "turns": 5}]
    },
    "Changes the weather to sunny for five turns.": {
        "damage": False,
        "effects": [{"type": "weather", "weather": "sun", "turns": 5}]
    },
    "Has a 20% chance to lower the target's Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": -1, "chance": 20, "target": "opponent"}]
    },
    "Inflicts twice the damage the user received from the last special hit it took.": {
        "damage": True,
        "counter": "special",
        "multiplier": 2,
        "effects": []
    },
    "Discards the user's stat changes and copies the target's.": {
        "damage": False,
        "effects": [{"type": "psych_up", "target": "opponent"}]
    },
    "Has a 10% chance to raise all of the user's stats by one stage.": {
        "damage": True,
        "effects": [{"type": "ancient_power", "chance": 10, "target": "self"}]
    },
    "Has a 20% chance to lower the target's Special Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "special_defense", "stages": -1, "chance": 20, "target": "opponent"}]
    },
    "Hits the target two turns later.": {
        "damage": True,
        "future_sight": True,
        "delay_turns": 2,
        "effects": []
    },
    "Has a 50% chance to lower the target's Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "defense", "stages": -1, "chance": 50, "target": "opponent"}]
    },
    "Prevents the target from leaving battle and inflicts 1/16 its max HP in damage for 2-5 turns.": {
        "damage": False,
        "effects": [{"type": "whirlpool", "min_turns": 2, "max_turns": 5, "damage_per_turn": 0.0625, "target": "opponent"}]
    },
    "Hits once for every conscious Pokémon the trainer has.": {
        "damage": True,
        "beat_up": True,
        "effects": []
    },
    "Can only be used as the first move after the user enters battle.  Causes the target to flinch.": {
        "damage": True,
        "first_turn_only": True,
        "effects": [{"type": "flinch", "chance": 100, "target": "opponent"}]
    },
    "Forced to use this move for several turns.  Pokémon cannot fall asleep in that time.": {
        "damage": True,
        "uproar": True,
        "effects": [{"type": "uproar_effect", "min_turns": 3, "max_turns": 3}]
    },
    "Stores energy up to three times for use with Spit Up and Swallow.": {
        "damage": False,
        "effects": [{"type": "stockpile", "target": "self"}]
    },
    "Power is 100 times the amount of energy Stockpiled.": {
        "damage": True,
        "spit_up": True,
        "effects": []
    },
    "Recovers 1/4 HP after one Stockpile, 1/2 HP after two Stockpiles, or full HP after three Stockpiles.": {
        "damage": False,
        "swallow": True,
        "effects": []
    },
    "Changes the weather to a hailstorm for five turns.": {
        "damage": False,
        "effects": [{"type": "weather", "weather": "hail", "turns": 5}]
    },
    "Prevents the target from using the same move twice in a row.": {
        "damage": False,
        "effects": [{"type": "torment", "target": "opponent"}]
    },
    "Raises the target's Special Attack by one stage and confuses the target.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "special_attack", "stages": 1, "target": "opponent"},
            {"type": "confusion", "chance": 100, "target": "opponent"}
        ]
    },
    "Burns the target.": {
        "damage": False,
        "effects": [{"type": "burn", "chance": 100, "target": "opponent"}]
    },
    "Lowers the target's Attack and Special Attack by two stages.  User faints.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": -2, "target": "opponent"},
            {"type": "stat_change", "stat": "special_attack", "stages": -2, "target": "opponent"},
            {"type": "self_destruct", "target": "self"}
        ]
    },
    "Power doubles if user is burned, paralyzed, or poisoned.": {
        "damage": True,
        "facade": True,
        "effects": []
    },
    "If the user takes damage before attacking, the attack is canceled.": {
        "damage": True,
        "focus_punch": True,
        "effects": []
    },
    "If the target is paralyzed, inflicts double damage and cures the paralysis.": {
        "damage": True,
        "smelling_salts": True,
        "effects": []
    },
    "Redirects the target's single-target effects to the user for this turn.": {
        "damage": False,
        "effects": [{"type": "follow_me", "target": "self"}]
    },
    "Uses a move which depends upon the terrain.": {
        "damage": True,
        "nature_power": True,
        "effects": []
    },
    "Raises the user's Special Defense by one stage.  User's Electric moves have doubled power next turn.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "special_defense", "stages": 1, "target": "self"},
            {"type": "charge", "target": "self"}
        ]
    },
    "For the next few turns, the target can only use damaging moves.": {
        "damage": False,
        "effects": [{"type": "taunt", "min_turns": 3, "max_turns": 3, "target": "opponent"}]
    },
    "Ally's next move inflicts half more damage.": {
        "damage": False,
        "effects": [{"type": "helping_hand", "target": "ally"}]
    },
    "User and target swap items.": {
        "damage": False,
        "effects": [{"type": "trick", "target": "opponent"}]
    },
    "Copies the target's ability.": {
        "damage": False,
        "effects": [{"type": "role_play", "target": "opponent"}]
    },
    "User will recover half its max HP at the end of the next turn.": {
        "damage": False,
        "effects": [{"type": "wish", "target": "self"}]
    },
    "Randomly selects and uses one of the trainer's other Pokémon's moves.": {
        "damage": False,
        "effects": [{"type": "assist"}]
    },
    "Prevents the user from leaving battle.  User regains 1/16 of its max HP every turn.": {
        "damage": False,
        "effects": [{"type": "ingrain", "heal_per_turn": 0.0625, "target": "self"}]
    },
    "Lowers the user's Attack and Defense by one stage after inflicting damage.": {
        "damage": True,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": -1, "target": "self"},
            {"type": "stat_change", "stat": "defense", "stages": -1, "target": "self"}
        ]
    },
    "Reflects back the first effect move used on the user this turn.": {
        "damage": False,
        "effects": [{"type": "magic_coat", "target": "self"}]
    },
    "User recovers the item it last used up.": {
        "damage": False,
        "effects": [{"type": "recycle", "target": "self"}]
    },
    "Inflicts double damage if the user takes damage before attacking this turn.": {
        "damage": True,
        "revenge": True,
        "effects": []
    },
    "Destroys Reflect and Light Screen.": {
        "damage": True,
        "effects": [{"type": "brick_break"}]
    },
    "Target sleeps at the end of the next turn.": {
        "damage": False,
        "effects": [{"type": "yawn", "target": "opponent"}]
    },
    "Target drops its held item.": {
        "damage": True,
        "effects": [{"type": "knock_off", "target": "opponent"}]
    },
    "Lowers the target's HP to equal the user's.": {
        "damage": False,
        "effects": [{"type": "endeavor", "target": "opponent"}]
    },
    "Inflicts more damage when the user has more HP remaining, with a maximum of 150 power.": {
        "damage": True,
        "eruption_based": True,
        "max_power": 150,
        "effects": []
    },
    "User and target swap abilities.": {
        "damage": False,
        "effects": [{"type": "skill_swap", "target": "opponent"}]
    },
    "Prevents the target from using any moves that the user also knows.": {
        "damage": False,
        "effects": [{"type": "imprison", "target": "opponent"}]
    },
    "Cleanses the user of a burn, paralysis, or poison.": {
        "damage": False,
        "effects": [{"type": "refresh", "target": "self"}]
    },
    "If the user faints this turn, the PP of the move that fainted it drops to 0.": {
        "damage": False,
        "effects": [{"type": "grudge", "target": "self"}]
    },
    "Steals the target's move, if it's self-targeted.": {
        "damage": False,
        "effects": [{"type": "snatch", "target": "opponent"}]
    },
    "Has a 30% chance to inflict a status effect which depends upon the terrain.": {
        "damage": True,
        "secret_power": True,
        "effects": []
    },
    "User dives underwater, dodging all attacks, and hits next turn.": {
        "damage": True,
        "semi_invulnerable_turns": 1,
        "effects": []
    },
    "User's type changes to match the terrain.": {
        "damage": False,
        "effects": [{"type": "camouflage", "target": "self"}]
    },
    "Raises the user's Special Attack by three stages.": {
        "damage": False,
        "effects": [{"type": "stat_change", "stat": "special_attack", "stages": 3, "target": "self"}]
    },
    "Has a 50% chance to lower the target's Special Defense by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "special_defense", "stages": -1, "chance": 50, "target": "opponent"}]
    },
    "Has a 50% chance to lower the target's Special Attack by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "special_attack", "stages": -1, "chance": 50, "target": "opponent"}]
    },
    "Has an increased chance for a critical hit and a 10% chance to burn the target.": {
        "damage": True,
        "critical_hit_ratio": 1,
        "effects": [{"type": "burn", "chance": 10, "target": "opponent"}]
    },
    "Halves all Electric-type damage.": {
        "damage": False,
        "effects": [{"type": "mud_sport", "target": "field"}]
    },
    "Has a 50% chance to badly poison the target.": {
        "damage": True,
        "effects": [{"type": "toxic", "chance": 50, "target": "opponent"}]
    },
    "Has a 20% chance to raise the user's Attack by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "attack", "stages": 1, "chance": 20, "target": "self"}]
    },
    "If there be weather, this move has doubled power and the weather's type.": {
        "damage": True,
        "weather_ball": True,
        "effects": []
    },
    "Lowers the user's Special Attack by two stages after inflicting damage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "special_attack", "stages": -2, "target": "self"}]
    },
    "Lowers the target's Attack and Defense by one stage.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": -1, "target": "opponent"},
            {"type": "stat_change", "stat": "defense", "stages": -1, "target": "opponent"}
        ]
    },
    "Raises the user's Defense and Special Defense by one stage.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "defense", "stages": 1, "target": "self"},
            {"type": "stat_change", "stat": "special_defense", "stages": 1, "target": "self"}
        ]
    },
    "Inflicts regular damage and can hit Bounce and Fly users.": {
        "damage": True,
        "can_hit_flying": True,
        "effects": []
    },
    "Has a 30% chance to lower the target's accuracy by one stage.": {
        "damage": True,
        "effects": [{"type": "stat_change", "stat": "accuracy", "stages": -1, "chance": 30, "target": "opponent"}]
    },
    "Raises the user's Attack and Defense by one stage.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": 1, "target": "self"},
            {"type": "stat_change", "stat": "defense", "stages": 1, "target": "self"}
        ]
    },
    "User bounces high into the air, dodging all attacks, and hits next turn.": {
        "damage": True,
        "semi_invulnerable_turns": 1,
        "effects": []
    },
    "Has an increased chance for a critical hit and a 10% chance to poison the target.": {
        "damage": True,
        "critical_hit_ratio": 1,
        "effects": [{"type": "poison", "chance": 10, "target": "opponent"}]
    },
    "User takes 1/3 the damage inflicted in recoil.  Has a 10% chance to paralyze the target.": {
        "damage": True,
        "recoil": 0.33,
        "effects": [{"type": "paralysis", "chance": 10, "target": "opponent"}]
    },
    "Halves all Fire-type damage.": {
        "damage": False,
        "effects": [{"type": "water_sport", "target": "field"}]
    },
    "Raises the user's Special Attack and Special Defense by one stage.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "special_attack", "stages": 1, "target": "self"},
            {"type": "stat_change", "stat": "special_defense", "stages": 1, "target": "self"}
        ]
    },
    "Raises the user's Attack and Speed by one stage.": {
        "damage": False,
        "effects": [
            {"type": "stat_change", "stat": "attack", "stages": 1, "target": "self"},
            {"type": "stat_change", "stat": "speed", "stages": 1, "target": "self"}
        ]
    }
}