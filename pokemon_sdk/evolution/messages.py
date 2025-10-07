from typing import Optional

class EvolutionMessages:
    @staticmethod
    def can_evolve(pokemon: str, evolution: str, extra_info: str = "") -> str:
        return (
            f"{pokemon} pode evoluir para **{evolution}**!{extra_info}\n"
            f"Você quer evoluir?\n"
            f"-# Você tem até 1 minuto para decidir."
        )
    
    @staticmethod
    def evolving() -> str:
        return "Evoluindo..."
    
    @staticmethod
    def evolved(user_id: str, old: str, new: str, emoji: str) -> str:
        return f"<@{user_id}> {emoji} {old} evoluiu para {new}!"
    
    @staticmethod
    def cancelled(user_id: str, pokemon: str, retry: bool = True) -> str:
        retry_text = " (Tentará novamente no próximo nível)" if retry else ""
        return f"<@{user_id}> {pokemon} não evoluiu.{retry_text}"
    
    @staticmethod
    def blocked(user_id: str, pokemon: str, unblock_cmd: str = "/desbloquear") -> str:
        return f"<@{user_id}> {pokemon} nunca evoluirá. (Use `{unblock_cmd}` para reverter)"
    
    @staticmethod
    def timeout(user_id: str, pokemon: str, retry: bool = True) -> str:
        retry_text = " (Tentará novamente no próximo nível)" if retry else ""
        return f"<@{user_id}> Tempo esgotado! {pokemon} não evoluiu.{retry_text}"
    
    @staticmethod
    def error(user_id: str, error: str) -> str:
        return f"<@{user_id}> Erro ao evoluir: {error}"
    
    @staticmethod
    def happiness_info(current: int, required: int) -> str:
        return f" (Felicidade: {current}/{required})"
    
    @staticmethod
    def time_info(time: str) -> str:
        from .config import TimeOfDay
        time_text = TimeOfDay.get_display_name(time)
        return f" ({time_text})" if time_text else ""
    
    @staticmethod
    def cannot_evolve(reason: Optional[str] = None) -> str:
        base = "Este Pokémon não pode evoluir"
        return f"{base}: {reason}" if reason else f"{base}."
    
    @staticmethod
    def blocked_evolution() -> str:
        return "Evolução bloqueada pelo treinador."
    
    @staticmethod
    def condition_not_met(condition: str) -> str:
        return f"Condição não atendida: {condition}"
    
    @staticmethod
    def no_evolution_found() -> str:
        return "Nenhuma evolução disponível."

class ButtonLabels:
    @staticmethod
    def evolve(evolution_name: str) -> str:
        return f"Evoluir para {evolution_name}"
    
    @staticmethod
    def cancel() -> str:
        return "Agora Não"
    
    @staticmethod
    def block() -> str:
        return "Nunca Evoluir"