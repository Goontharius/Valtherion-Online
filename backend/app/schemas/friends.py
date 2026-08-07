from pydantic import BaseModel


class FriendAdd(BaseModel):
    username: str


class FriendRemove(BaseModel):
    username: str
