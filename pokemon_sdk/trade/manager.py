import discord
import asyncio
from typing import Optional, Dict, List, Set, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

class TradeState(Enum):
    PENDING = "pending"
    OFFERING = "offering"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

@dataclass
class TradeOffer:
    pokemon_ids: List[int] = field(default_factory=list)
    items: Dict[str, int] = field(default_factory=dict)
    money: int = 0
    confirmed: bool = False
    
    def is_empty(self) -> bool:
        return not self.pokemon_ids and not self.items and self.money == 0
    
    def get_pokemon_count(self) -> int:
        return len(self.pokemon_ids)
    
    def get_item_count(self) -> int:
        return sum(self.items.values())

@dataclass
class TradeSession:
    trade_id: str
    initiator_id: str
    partner_id: str
    initiator_offer: TradeOffer = field(default_factory=TradeOffer)
    partner_offer: TradeOffer = field(default_factory=TradeOffer)
    state: TradeState = TradeState.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))
    message: Optional[discord.Message] = None
    channel_id: Optional[int] = None
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def get_offer(self, user_id: str) -> TradeOffer:
        return self.initiator_offer if user_id == self.initiator_id else self.partner_offer
    
    def get_partner_offer(self, user_id: str) -> TradeOffer:
        return self.partner_offer if user_id == self.initiator_id else self.initiator_offer
    
    def get_partner_id(self, user_id: str) -> str:
        return self.partner_id if user_id == self.initiator_id else self.initiator_id
    
    def both_confirmed(self) -> bool:
        return self.initiator_offer.confirmed and self.partner_offer.confirmed
    
    def reset_confirmations(self) -> None:
        self.initiator_offer.confirmed = False
        self.partner_offer.confirmed = False

class TradeManager:
    def __init__(self, toolkit, pokemon_manager):
        self.tk = toolkit
        self.pm = pokemon_manager
        self._active_trades: Dict[str, TradeSession] = {}
        self._user_trades: Dict[str, str] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._trade_counter = 0
    
    def _get_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]
    
    def _generate_trade_id(self) -> str:
        self._trade_counter += 1
        return f"trade_{self._trade_counter}_{int(datetime.now(timezone.utc).timestamp())}"
    
    def is_trading(self, user_id: str) -> bool:
        if user_id not in self._user_trades:
            return False
        
        trade_id = self._user_trades[user_id]
        trade = self._active_trades.get(trade_id)
        
        if not trade:
            del self._user_trades[user_id]
            return False
        
        if trade.is_expired():
            self._cleanup_trade(trade_id)
            return False
        
        return True
    
    def get_active_trade(self, user_id: str) -> Optional[TradeSession]:
        if not self.is_trading(user_id):
            return None
        
        trade_id = self._user_trades[user_id]
        return self._active_trades.get(trade_id)
    
    async def create_trade(self, initiator_id: str, partner_id: str) -> TradeSession:
        if self.is_trading(initiator_id):
            raise ValueError("Você já está em uma trade ativa!")
        
        if self.is_trading(partner_id):
            raise ValueError("Este usuário já está em uma trade ativa!")
        
        trade_id = self._generate_trade_id()
        
        trade = TradeSession(
            trade_id=trade_id,
            initiator_id=initiator_id,
            partner_id=partner_id
        )
        
        self._active_trades[trade_id] = trade
        self._user_trades[initiator_id] = trade_id
        self._user_trades[partner_id] = trade_id
        
        return trade
    
    def _cleanup_trade(self, trade_id: str) -> None:
        if trade_id not in self._active_trades:
            return
        
        trade = self._active_trades[trade_id]
        
        if trade.initiator_id in self._user_trades:
            del self._user_trades[trade.initiator_id]
        
        if trade.partner_id in self._user_trades:
            del self._user_trades[trade.partner_id]
        
        del self._active_trades[trade_id]
    
    async def cancel_trade(self, trade_id: str, reason: str = "cancelada") -> None:
        if trade_id not in self._active_trades:
            return
        
        trade = self._active_trades[trade_id]
        trade.state = TradeState.CANCELLED
        
        self._cleanup_trade(trade_id)
    
    async def validate_pokemon_offer(
        self, 
        user_id: str, 
        pokemon_ids: List[int]
    ) -> Tuple[bool, Optional[str]]:
        if not pokemon_ids:
            return True, None
        
        try:
            user_pokemon = self.tk.list_pokemon_by_owner(user_id)
            user_pokemon_ids = {p["id"] for p in user_pokemon}
            
            for pid in pokemon_ids:
                if pid not in user_pokemon_ids:
                    return False, f"Você não possui o Pokémon #{pid}"
                
                pokemon = self.tk.get_pokemon(user_id, pid)
                
                if pokemon.get("is_favorite"):
                    from utils.formatting import format_pokemon_display
                    return False, f"{format_pokemon_display(pokemon, bold_name=True)} está marcado como favorito"
            
            return True, None
            
        except Exception as e:
            return False, f"Erro ao validar Pokémon: {str(e)}"
    
    async def validate_item_offer(
        self,
        user_id: str,
        items: Dict[str, int]
    ) -> Tuple[bool, Optional[str]]:
        if not items:
            return True, None
        
        try:
            for item_id, quantity in items.items():
                if quantity <= 0:
                    return False, f"Quantidade inválida para {item_id}"
                
                if not self.tk.has_item(user_id, item_id, quantity):
                    item_name = self.pm.get_item_name(item_id)
                    user_qty = self.tk.get_item_quantity(user_id, item_id)
                    return False, f"Você não tem {quantity}x **{item_name}** (você tem: {user_qty})"
            
            return True, None
            
        except Exception as e:
            return False, f"Erro ao validar itens: {str(e)}"
    
    async def validate_money_offer(
        self,
        user_id: str,
        amount: int
    ) -> Tuple[bool, Optional[str]]:
        if amount <= 0:
            return True, None
        
        try:
            user = self.tk.get_user(user_id)
            if user["money"] < amount:
                return False, f"Você não tem ₽{amount:,} (você tem: ₽{user['money']:,})"
            
            return True, None
            
        except Exception as e:
            return False, f"Erro ao validar dinheiro: {str(e)}"
    
    async def add_pokemon_to_offer(
        self,
        trade_id: str,
        user_id: str,
        pokemon_ids: List[int]
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        offer = trade.get_offer(user_id)
        
        pokemon_ids = list(set(pokemon_ids))
        
        valid, error = await self.validate_pokemon_offer(user_id, pokemon_ids)
        if not valid:
            return False, error
        
        for pid in pokemon_ids:
            if pid not in offer.pokemon_ids:
                offer.pokemon_ids.append(pid)
        
        trade.reset_confirmations()
        trade.state = TradeState.OFFERING
        
        return True, None
    
    async def remove_pokemon_from_offer(
        self,
        trade_id: str,
        user_id: str,
        pokemon_ids: List[int]
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        offer = trade.get_offer(user_id)
        
        for pid in pokemon_ids:
            if pid in offer.pokemon_ids:
                offer.pokemon_ids.remove(pid)
        
        trade.reset_confirmations()
        
        return True, None
    
    async def add_items_to_offer(
        self,
        trade_id: str,
        user_id: str,
        items: Dict[str, int]
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        offer = trade.get_offer(user_id)
        
        valid, error = await self.validate_item_offer(user_id, items)
        if not valid:
            return False, error
        
        for item_id, quantity in items.items():
            offer.items[item_id] = offer.items.get(item_id, 0) + quantity
        
        trade.reset_confirmations()
        trade.state = TradeState.OFFERING
        
        return True, None
    
    async def remove_items_from_offer(
        self,
        trade_id: str,
        user_id: str,
        items: Dict[str, int]
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        offer = trade.get_offer(user_id)
        
        for item_id, quantity in items.items():
            if item_id in offer.items:
                offer.items[item_id] -= quantity
                if offer.items[item_id] <= 0:
                    del offer.items[item_id]
        
        trade.reset_confirmations()
        
        return True, None
    
    async def set_money_offer(
        self,
        trade_id: str,
        user_id: str,
        amount: int
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        if amount < 0:
            return False, "Quantidade inválida"
        
        valid, error = await self.validate_money_offer(user_id, amount)
        if not valid:
            return False, error
        
        offer = trade.get_offer(user_id)
        offer.money = amount
        
        trade.reset_confirmations()
        trade.state = TradeState.OFFERING
        
        return True, None
    
    async def confirm_offer(
        self,
        trade_id: str,
        user_id: str
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        offer = trade.get_offer(user_id)
        partner_offer = trade.get_partner_offer(user_id)
        
        if offer.is_empty() and partner_offer.is_empty():
            return False, "Ambas as ofertas estão vazias!"
        
        if offer.pokemon_ids:
            valid, error = await self.validate_pokemon_offer(user_id, offer.pokemon_ids)
            if not valid:
                return False, f"Sua oferta não é mais válida: {error}"
        
        if offer.items:
            valid, error = await self.validate_item_offer(user_id, offer.items)
            if not valid:
                return False, f"Sua oferta não é mais válida: {error}"
        
        if offer.money > 0:
            valid, error = await self.validate_money_offer(user_id, offer.money)
            if not valid:
                return False, f"Sua oferta não é mais válida: {error}"
        
        offer.confirmed = True
        trade.state = TradeState.CONFIRMING
        
        return True, None
    
    async def execute_trade(
        self,
        trade_id: str,
        channel: discord.abc.Messageable
    ) -> Tuple[bool, Optional[str]]:
        trade = self._active_trades.get(trade_id)
        if not trade:
            return False, "Trade não encontrada"
        
        if not trade.both_confirmed():
            return False, "Ambos os usuários precisam confirmar"
        
        async with self._get_lock(trade.initiator_id):
            async with self._get_lock(trade.partner_id):
                try:
                    for user_id, offer in [
                        (trade.initiator_id, trade.initiator_offer),
                        (trade.partner_id, trade.partner_offer)
                    ]:
                        if offer.pokemon_ids:
                            valid, error = await self.validate_pokemon_offer(user_id, offer.pokemon_ids)
                            if not valid:
                                self._cleanup_trade(trade_id)
                                return False, f"Oferta inválida: {error}"
                        
                        if offer.items:
                            valid, error = await self.validate_item_offer(user_id, offer.items)
                            if not valid:
                                self._cleanup_trade(trade_id)
                                return False, f"Oferta inválida: {error}"
                        
                        if offer.money > 0:
                            valid, error = await self.validate_money_offer(user_id, offer.money)
                            if not valid:
                                self._cleanup_trade(trade_id)
                                return False, f"Oferta inválida: {error}"
                    
                    await self._transfer_pokemon(
                        trade.initiator_id,
                        trade.partner_id,
                        trade.initiator_offer.pokemon_ids,
                        trade.partner_offer.pokemon_ids
                    )
                    
                    await self._transfer_items(
                        trade.initiator_id,
                        trade.partner_id,
                        trade.initiator_offer.items,
                        trade.partner_offer.items
                    )
                    
                    await self._transfer_money(
                        trade.initiator_id,
                        trade.partner_id,
                        trade.initiator_offer.money,
                        trade.partner_offer.money
                    )
                    
                    trade.state = TradeState.COMPLETED
                    
                    self._cleanup_trade(trade_id)
                    
                except Exception as e:
                    self._cleanup_trade(trade_id)
                    return False, f"Erro ao executar trade: {str(e)}"
        
        try:
            await self._check_trade_evolutions(trade, channel)
        except Exception as e:
            print(f"Erro ao verificar evoluções: {e}")
        
        return True, None
    
    async def _check_trade_evolutions(
        self,
        trade: TradeSession,
        channel: discord.abc.Messageable
    ) -> None:
        from pokemon_sdk.evolution import EvolutionTriggers
        from utils.formatting import format_pokemon_display
        
        all_traded_pokemon = [
            (trade.initiator_id, trade.partner_offer.pokemon_ids),
            (trade.partner_id, trade.initiator_offer.pokemon_ids)
        ]
        
        for new_owner_id, pokemon_ids in all_traded_pokemon:
            for pid in pokemon_ids:
                try:
                    pokemon = self.tk.get_pokemon(new_owner_id, pid)
                    
                    evolution_data = self.pm.check_evolution(
                        new_owner_id,
                        pid,
                        EvolutionTriggers.TRADE
                    )
                    
                    if evolution_data:
                        if "evolves_to_id" in evolution_data and "species_id" not in evolution_data:
                            evolution_data["species_id"] = evolution_data["evolves_to_id"]
                        
                        if "name" not in evolution_data:
                            try:
                                evo_species = self.pm.service.get_species(evolution_data["species_id"])
                                evolution_data["name"] = evo_species.name.title()
                            except:
                                evolution_data["name"] = f"#{evolution_data['species_id']}"
                        
                        temp_message = await channel.send(
                            f"<@{new_owner_id}> {format_pokemon_display(pokemon, bold_name=True)} pode evoluir após a troca!"
                        )
                        
                        await self.pm.evolution_ui.show_evolution_choice(
                            message=temp_message,
                            owner_id=new_owner_id,
                            pokemon_id=pid,
                            pokemon=pokemon,
                            evolution_data=evolution_data
                        )
                        
                except Exception as e:
                    print(f"Erro ao verificar evolução por trade: {e}")
                    continue
    
    async def _transfer_pokemon(
        self,
        user1_id: str,
        user2_id: str,
        user1_pokemon: List[int],
        user2_pokemon: List[int]
    ) -> None:
        for pid in user1_pokemon:
            self.tk.transfer_pokemon(user1_id, pid, user2_id)
        
        for pid in user2_pokemon:
            self.tk.transfer_pokemon(user2_id, pid, user1_id)
    
    async def _transfer_items(
        self,
        user1_id: str,
        user2_id: str,
        user1_items: Dict[str, int],
        user2_items: Dict[str, int]
    ) -> None:
        for item_id, quantity in user1_items.items():
            self.tk.transfer_item(user1_id, user2_id, item_id, quantity)
        
        for item_id, quantity in user2_items.items():
            self.tk.transfer_item(user2_id, user1_id, item_id, quantity)
    
    async def _transfer_money(
        self,
        user1_id: str,
        user2_id: str,
        user1_money: int,
        user2_money: int
    ) -> None:
        if user1_money > 0:
            self.tk.adjust_money(user1_id, -user1_money)
            self.tk.adjust_money(user2_id, user1_money)
        
        if user2_money > 0:
            self.tk.adjust_money(user2_id, -user2_money)
            self.tk.adjust_money(user1_id, user2_money)
