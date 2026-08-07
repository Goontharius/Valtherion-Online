from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class QuestAccept(BaseModel):
    quest_id: str


class QuestProgress(BaseModel):
    quest_id: str
    objective_index: int
    progress_amount: int = 1


class QuestComplete(BaseModel):
    quest_id: str
