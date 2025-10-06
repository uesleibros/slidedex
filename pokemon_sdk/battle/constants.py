class BattleConstants:
	BURN_DAMAGE_RATIO = 1/16
	POISON_DAMAGE_RATIO = 1/8
	TOXIC_BASE_RATIO = 1/16
	LEECH_SEED_RATIO = 1/8
	INGRAIN_HEAL_RATIO = 1/16
	HAIL_DAMAGE_RATIO = 1/16
	
	PARALYSIS_SPEED_MULT = 0.5
	PARALYSIS_PROC_CHANCE = 0.25
	BURN_ATK_MULT = 0.5
	
	CONFUSION_SELF_HIT_CHANCE = 0.33
	FREEZE_THAW_CHANCE = 0.2
	CONFUSION_MIN_TURNS = 2
	CONFUSION_MAX_TURNS = 4
	
	WEATHER_BOOST_MULT = 1.5
	WEATHER_NERF_MULT = 0.5
	
	SCREEN_DEF_MULT = 1.5
	STAB_MULT = 1.5
	
	MAX_STAT_STAGE = 6
	MIN_STAT_STAGE = -6
	
	CRIT_BASE_CHANCE = 0.0625
	CRIT_DAMAGE_MULT = 1.5
	
	STRUGGLE_RECOIL_RATIO = 0.25
	
	DAMAGE_ROLL_MIN = 0.85
	DAMAGE_ROLL_MAX = 1.0
	
	CAPTURE_MAX_VALUE = 255
	CAPTURE_RANGE = 65536
	
	SLEEP_STATUS_BONUS = 2.5
	PARA_STATUS_BONUS = 1.5

STAT_NAMES = {
	"atk": "Ataque",
	"def": "Defesa",
	"sp_atk": "Ataque Especial",
	"sp_def": "Defesa Especial",
	"speed": "Velocidade",
	"accuracy": "Precisão",
	"evasion": "Evasão"
}

STATUS_TAGS = {
	"burn": "<:brnstatus:1424614707884457994>",
	"poison": "<:psnstatus:1424615771987902496>",
	"paralysis": "<:przstatus:1424614450614505492>",
	"sleep": "<:slpstatus:1424614954325246072>",
	"freeze": "<:frzstatus:1424615357473230944>",
	"toxic": "<:psnstatus:1424615771987902496>"
}

STATUS_MESSAGES = {
	"burn": "foi queimado",
	"poison": "foi envenenado",
	"paralysis": "foi paralisado",
	"sleep": "adormeceu",
	"freeze": "foi congelado",
	"toxic": "foi gravemente envenenado",
	"confusion": "ficou confuso"
}

STAT_MAP = {
	"attack": "atk",
	"defense": "def",
	"special_attack": "sp_atk",
	"special-attack": "sp_atk",
	"special_defense": "sp_def",
	"special-defense": "sp_def",
	"speed": "speed",
	"accuracy": "accuracy",
	"evasion": "evasion"
}
