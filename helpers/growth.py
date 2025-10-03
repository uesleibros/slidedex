class GrowthRate:
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"
    MEDIUM_SLOW = "medium-slow"
    SLOW_THEN_VERY_FAST = "slow-then-very-fast"
    FAST_THEN_VERY_SLOW = "fast-then-very-slow"
    
    @staticmethod
    def calculate_exp(growth_type: str, level: int) -> int:
        x = level
        
        if growth_type == GrowthRate.SLOW:
            return int((5 * x**3) / 4)
        
        elif growth_type == GrowthRate.MEDIUM:
            return int(x**3)
        
        elif growth_type == GrowthRate.FAST:
            return int((4 * x**3) / 5)
        
        elif growth_type == GrowthRate.MEDIUM_SLOW:
            return int((6 * x**3) / 5 - 15 * x**2 + 100 * x - 140)
        
        elif growth_type == GrowthRate.SLOW_THEN_VERY_FAST:
            if x <= 50:
                return int((x**3 * (100 - x)) / 50)
            elif x <= 68:
                return int((x**3 * (150 - x)) / 100)
            elif x <= 98:
                mod = x % 3
                floor_div = x // 3
                return int((x**3 * (1274 + mod**2 - 9 * mod - 20 * floor_div)) / 1000)
            else:
                return int((x**3 * (160 - x)) / 100)
        
        elif growth_type == GrowthRate.FAST_THEN_VERY_SLOW:
            if x <= 15:
                return int((x**3 * (24 + (x + 1) // 3)) / 50)
            elif x <= 35:
                return int((x**3 * (14 + x)) / 50)
            else:
                return int((x**3 * (32 + x // 2)) / 50)
        
        else:
            raise ValueError(f"Growth type '{growth_type}' inválido")
    
    @staticmethod
    def get_level_from_exp(growth_type: str, exp: int) -> int:
        for level in range(1, 101):
            if GrowthRate.calculate_exp(growth_type, level) > exp:
                return level - 1
        return 100
    
    @staticmethod
    def get_exp_for_next_level(growth_type: str, current_level: int) -> int:
        if current_level >= 100:
            return 0
        current_exp = GrowthRate.calculate_exp(growth_type, current_level)
        next_exp = GrowthRate.calculate_exp(growth_type, current_level + 1)
        return next_exp - current_exp


GROWTH_RATE_INFO = {
    GrowthRate.SLOW: {"name": "Slow", "max_exp": 1250000},
    GrowthRate.MEDIUM: {"name": "Medium", "max_exp": 1000000},
    GrowthRate.FAST: {"name": "Fast", "max_exp": 800000},
    GrowthRate.MEDIUM_SLOW: {"name": "Medium Slow", "max_exp": 1059860},
    GrowthRate.SLOW_THEN_VERY_FAST: {"name": "Erratic", "max_exp": 600000},
    GrowthRate.FAST_THEN_VERY_SLOW: {"name": "Fluctuating", "max_exp": 1640000}
}
