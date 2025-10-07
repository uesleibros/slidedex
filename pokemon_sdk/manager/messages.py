from typing import Dict, Any

class Messages:
    @staticmethod
    def not_your_choice() -> str:
        return "Essa escolha não é sua!"
    
    @staticmethod
    def already_answered() -> str:
        return "Já foi respondido!"
    
    @staticmethod
    def evolving() -> str:
        return "Evoluindo..."
    
    @staticmethod
    def evolved(user_id: str, old_pokemon: str, new_pokemon: str, emoji: str) -> str:
        return f"<@{user_id}> {emoji} {old_pokemon} evoluiu para {new_pokemon}!"
    
    @staticmethod
    def evolution_error(user_id: str, error: str) -> str:
        return f"<@{user_id}> Erro ao evoluir: {error}"
    
    @staticmethod
    def evolution_cancelled(user_id: str, pokemon_name: str) -> str:
        return f"<@{user_id}> {pokemon_name} não evoluiu. (Tentará novamente no próximo nível)"
    
    @staticmethod
    def evolution_blocked(user_id: str, pokemon_name: str) -> str:
        return f"<@{user_id}> {pokemon_name} nunca evoluirá. (Use `/desbloquear` para reverter)"
    
    @staticmethod
    def evolution_timeout(user_id: str, pokemon_name: str) -> str:
        return f"<@{user_id}> Tempo esgotado! {pokemon_name} não evoluiu. (Tentará novamente no próximo nível)"
    
    @staticmethod
    def move_learned(user_id: str, pokemon: str, old_move: str, new_move: str) -> str:
        return f"<@{user_id}> {pokemon} Esqueceu **{old_move}** e Aprendeu **{new_move}**!"
    
    @staticmethod
    def move_not_learned(user_id: str, pokemon: str, move: str) -> str:
        return f"<@{user_id}> {pokemon} Não aprendeu **{move}**."
    
    @staticmethod
    def move_timeout(user_id: str, pokemon: str, move: str) -> str:
        return f"<@{user_id}> Tempo esgotado! {pokemon} não aprendeu **{move}**."
    
    @staticmethod
    def evolution_choice(user_id: str, pokemon: str, evolution_name: str, extra_info: str = "") -> str:
        return (
            f"<@{user_id}> {pokemon} pode evoluir para **{evolution_name}**!{extra_info}\n"
            f"Você quer evoluir?\n"
            f"-# Você tem até 1 minuto para decidir."
        )
    
    @staticmethod
    def move_choice(user_id: str, pokemon: str, move_name: str) -> str:
        return (
            f"<@{user_id}> {pokemon} Quer aprender **{move_name}**, mas já conhece 4 movimentos.\n"
            f"Escolha um movimento para esquecer ou cancele para não aprender **{move_name}**.\n"
            f"-# Você tem até 1 minuto para fazer sua escolha."
        )
    
    @staticmethod
    def max_level_reached(pokemon: str, level: int) -> str:
        return f"{pokemon} atingiu o **nível máximo {level}**!"
    
    @staticmethod
    def level_up(pokemon: str, level: int, emoji: str) -> str:
        return f"{emoji} {pokemon} Subiu para o nivel **{level}**!"
    
    @staticmethod
    def item_not_found(item_id: str) -> str:
        return f"Item '{item_id}' não encontrado na PokeAPI"
    
    @staticmethod
    def item_unavailable(item_id: str) -> str:
        return f"Item `{item_id}` não está disponível na Gen 3"
    
    @staticmethod
    def format_happiness_info(happiness: int, required: int) -> str:
        return f" (Felicidade: {happiness}/{required})"
    
    @staticmethod
    def format_time_info(time_of_day: str) -> str:
        time_text = "Dia" if time_of_day == "day" else "Noite"
        return f" ({time_text})"

class ButtonLabels:
    @staticmethod
    def evolve(evolution_name: str) -> str:
        return f"Evoluir para {evolution_name}"
    
    @staticmethod
    def cancel() -> str:
        return "Agora Não"
    
    @staticmethod
    def block_evolution() -> str:
        return "Nunca Evoluir"
    
    @staticmethod
    def forget_move(move_name: str) -> str:
        return f"Esquecer {move_name}"
    
    @staticmethod
    def cancel_move() -> str:
        return "Cancelar"