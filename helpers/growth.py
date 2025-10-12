from enum import Enum
from dataclasses import dataclass
from typing import Final
from functools import lru_cache

@dataclass(frozen=True)
class GrowthRateInfo:
    name: str
    max_exp: int

class GrowthRate(str, Enum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"
    MEDIUM_SLOW = "medium-slow"
    ERRATIC = "slow-then-very-fast"
    FLUCTUATING = "fast-then-very-slow"

GROWTH_INFO: Final[dict[GrowthRate, GrowthRateInfo]] = {
    GrowthRate.SLOW: GrowthRateInfo("Slow", 1_250_000),
    GrowthRate.MEDIUM: GrowthRateInfo("Medium", 1_000_000),
    GrowthRate.FAST: GrowthRateInfo("Fast", 800_000),
    GrowthRate.MEDIUM_SLOW: GrowthRateInfo("Medium Slow", 1_059_860),
    GrowthRate.ERRATIC: GrowthRateInfo("Erratic", 600_000),
    GrowthRate.FLUCTUATING: GrowthRateInfo("Fluctuating", 1_640_000),
}

MAX_LEVEL: Final[int] = 100
MIN_LEVEL: Final[int] = 1

class ExperienceCalculator:
    @staticmethod
    @lru_cache(maxsize=600)
    def calculate(growth_type: str, level: int) -> int:
        if level < MIN_LEVEL or level > MAX_LEVEL:
            raise ValueError(f"Level must be between {MIN_LEVEL} and {MAX_LEVEL}")
        
        calculators = {
            GrowthRate.SLOW: ExperienceCalculator._slow,
            GrowthRate.MEDIUM: ExperienceCalculator._medium,
            GrowthRate.FAST: ExperienceCalculator._fast,
            GrowthRate.MEDIUM_SLOW: ExperienceCalculator._medium_slow,
            GrowthRate.ERRATIC: ExperienceCalculator._erratic,
            GrowthRate.FLUCTUATING: ExperienceCalculator._fluctuating,
        }
        
        calculator = calculators.get(growth_type)
        
        if not calculator:
            raise ValueError(f"Invalid growth type: {growth_type}")
        
        return calculator(level)
    
    @staticmethod
    def _slow(level: int) -> int:
        return int((5 * level**3) / 4)
    
    @staticmethod
    def _medium(level: int) -> int:
        return int(level**3)
    
    @staticmethod
    def _fast(level: int) -> int:
        return int((4 * level**3) / 5)
    
    @staticmethod
    def _medium_slow(level: int) -> int:
        return int((6 * level**3) / 5 - 15 * level**2 + 100 * level - 140)
    
    @staticmethod
    def _erratic(level: int) -> int:
        if level <= 50:
            return int((level**3 * (100 - level)) / 50)
        
        if level <= 68:
            return int((level**3 * (150 - level)) / 100)
        
        if level <= 98:
            mod = level % 3
            floor_div = level // 3
            return int((level**3 * (1274 + mod**2 - 9 * mod - 20 * floor_div)) / 1000)
        
        return int((level**3 * (160 - level)) / 100)
    
    @staticmethod
    def _fluctuating(level: int) -> int:
        if level <= 15:
            return int((level**3 * (24 + (level + 1) // 3)) / 50)
        
        if level <= 35:
            return int((level**3 * (14 + level)) / 50)
        
        return int((level**3 * (32 + level // 2)) / 50)
    
    @staticmethod
    def get_level(growth_type: str, exp: int) -> int:
        if exp <= 0:
            return MIN_LEVEL
        
        for level in range(MIN_LEVEL, MAX_LEVEL + 1):
            if ExperienceCalculator.calculate(growth_type, level) > exp:
                return max(MIN_LEVEL, level - 1)
        
        return MAX_LEVEL
    
    @staticmethod
    def get_next_level_exp(growth_type: str, current_level: int) -> int:
        if current_level >= MAX_LEVEL:
            return 0
        
        current_exp = ExperienceCalculator.calculate(growth_type, current_level)
        next_exp = ExperienceCalculator.calculate(growth_type, current_level + 1)
        
        return next_exp - current_exp
    
    @staticmethod
    def get_exp_to_level(growth_type: str, current_exp: int, target_level: int) -> int:
        if target_level > MAX_LEVEL:
            target_level = MAX_LEVEL
        
        target_exp = ExperienceCalculator.calculate(growth_type, target_level)
        return max(0, target_exp - current_exp)
    
    @staticmethod
    def get_progress(growth_type: str, current_exp: int) -> dict[str, int | float]:
        current_level = ExperienceCalculator.get_level(growth_type, current_exp)
        
        if current_level >= MAX_LEVEL:
            return {
                "current_level": MAX_LEVEL,
                "current_exp": current_exp,
                "exp_for_current": ExperienceCalculator.calculate(growth_type, MAX_LEVEL),
                "exp_for_next": 0,
                "exp_needed": 0,
                "exp_in_level": 0,
                "progress_percent": 100.0
            }
        
        exp_for_current = ExperienceCalculator.calculate(growth_type, current_level)
        exp_for_next = ExperienceCalculator.calculate(growth_type, current_level + 1)
        
        exp_in_level = current_exp - exp_for_current
        exp_required = exp_for_next - exp_for_current
        
        progress = (exp_in_level / exp_required * 100.0) if exp_required > 0 else 0.0
        
        return {
            "current_level": current_level,
            "current_exp": current_exp,
            "exp_for_current": exp_for_current,
            "exp_for_next": exp_for_next,
            "exp_needed": exp_for_next - current_exp,
            "exp_in_level": exp_in_level,
            "progress_percent": round(progress, 2)
        }

@dataclass(frozen=True)
class LevelRange:
    start: int
    end: int
    
    def __post_init__(self):
        if self.start < MIN_LEVEL or self.end > MAX_LEVEL:
            raise ValueError(f"Level range must be between {MIN_LEVEL} and {MAX_LEVEL}")
        if self.start > self.end:
            raise ValueError("Start level cannot be greater than end level")
    
    def get_exp_table(self, growth_type: str) -> list[tuple[int, int]]:
        return [
            (level, ExperienceCalculator.calculate(growth_type, level))
            for level in range(self.start, self.end + 1)
        ]