from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class TradeOffer(BaseModel):
    target_player: str
    offered_items: Dict[str, int] = {}
    offered_currency: Dict[str, int] = {}
    requested_items: Dict[str, int] = {}
    requested_currency: Dict[str, int] = {}


class TradeResponse(BaseModel):
    trade_id: str
    accepted: bool
    message: Optional[str] = None


class TradeAction(BaseModel):
    trade_id: str
