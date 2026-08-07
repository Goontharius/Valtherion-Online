from pydantic import BaseModel
from typing import Dict


class BankDeposit(BaseModel):
    items: Dict[str, int] = {}
    currency: Dict[str, int] = {}


class BankWithdraw(BaseModel):
    items: Dict[str, int] = {}
    currency: Dict[str, int] = {}
