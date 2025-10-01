from typing import Optional
from .constants import STAT_NAMES, STATUS_MESSAGES

class BattleMessages:
    
    @staticmethod
    def damage(attacker: str, move: str, damage: int, special: str = "") -> str:
        base = f"{attacker} usou **{move}**!"
        if damage > 0:
            base += f" ({damage} de dano)"
        if special:
            base += f" {special}"
        return base
    
    @staticmethod
    def status_applied(pokemon: str, status: str) -> str:
        icons = {
            "burn": "🔥",
            "poison": "☠️",
            "paralysis": "⚡",
            "sleep": "💤",
            "freeze": "❄️",
            "toxic": "☠️☠️"
        }
        icon = icons.get(status, "💫")
        msg = STATUS_MESSAGES.get(status, "foi afetado")
        return f"   └─ {icon} {pokemon} {msg}!"
    
    @staticmethod
    def stat_change(pokemon: str, stat: str, stages: int) -> str:
        stat_name = STAT_NAMES.get(stat, stat)
        if stages > 0:
            arrows = "↑" * abs(stages)
            level = "drasticamente" if abs(stages) >= 2 else ""
            return f"   └─ 📈 {stat_name} de {pokemon} aumentou {level} {arrows}".strip()
        else:
            arrows = "↓" * abs(stages)
            level = "drasticamente" if abs(stages) >= 2 else ""
            return f"   └─ 📉 {stat_name} de {pokemon} diminuiu {level} {arrows}".strip()
    
    @staticmethod
    def stat_maxed(pokemon: str, stat: str, is_max: bool = True) -> str:
        stat_name = STAT_NAMES.get(stat, stat)
        limit = "máximo" if is_max else "mínimo"
        return f"   └─ 💢 {stat_name} de {pokemon} já está no {limit}!"
    
    @staticmethod
    def healing(pokemon: str, amount: int) -> str:
        return f"   └─ 💚 {pokemon} recuperou {amount} HP!"
    
    @staticmethod
    def recoil(pokemon: str, amount: int) -> str:
        return f"   └─ 💥 {pokemon} sofreu {amount} de recuo!"
    
    @staticmethod
    def drain(pokemon: str, amount: int) -> str:
        return f"   └─ 💉 {pokemon} drenou {amount} HP!"
    
    @staticmethod
    def fainted(pokemon: str) -> str:
        return f"💀 **{pokemon} foi derrotado!**"
    
    @staticmethod
    def miss(pokemon: str, move: str) -> str:
        return f"💨 {pokemon} usou **{move}**, mas errou!"
    
    @staticmethod
    def no_effect(pokemon: str, move: str) -> str:
        return f"🚫 {pokemon} usou **{move}**!\n   └─ Não teve efeito!"
    
    @staticmethod
    def protected(pokemon: str) -> str:
        return f"🛡️ {pokemon} se protegeu do ataque!"
    
    @staticmethod
    def immune(pokemon: str, reason: str) -> str:
        return f"   └─ 💢 {pokemon} {reason}!"
    
    @staticmethod
    def failed(move: str = None) -> str:
        if move:
            return f"   └─ 💢 **{move}** falhou!"
        return "   └─ 💢 Mas falhou!"
    
    @staticmethod
    def details(hits: Optional[int] = None, crit: bool = False, effectiveness: float = 1.0) -> Optional[str]:
        parts = []
        if hits and hits > 1:
            parts.append(f"🎯 {hits}x")
        if crit:
            parts.append("💥 CRÍTICO")
        if effectiveness > 1.0:
            parts.append("✨ Super eficaz")
        elif 0 < effectiveness < 1.0:
            parts.append("💢 Pouco eficaz")
        
        return "   └─ " + " • ".join(parts) if parts else None
