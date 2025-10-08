import discord
import asyncio
from typing import Optional, Dict, List, Set, Tuple
from datetime import timedelta
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
    created_at: discord.utils.utcnow = field(default_factory=discord.utils.utcnow)
    expires_at: discord.utils.utcnow = field(default_factory=lambda: discord.utils.utcnow() + timedelta(minutes=10))
    message: Optional[discord.Message] = None
    channel_id: Optional[int] = None
    
    def is_expired(self) -> bool:
        return discord.utils.utcnow() > self.expires_at
    
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
