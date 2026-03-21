from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PollOptionBase(BaseModel):
    text: str


class PollOptionCreate(PollOptionBase):
    pass


class PollOption(PollOptionBase):
    id: int
    poll_id: int
    votes_count: int

    class Config:
        from_attributes = True


class PollBase(BaseModel):
    title: str
    description: Optional[str] = None


class PollCreate(PollBase):
    options: List[str]


class Poll(PollBase):
    id: int
    creator_id: int
    created_at: datetime
    options: List[PollOption] = []

    class Config:
        from_attributes = True


class VoteCreate(BaseModel):
    poll_id: int
    option_id: int
