from pydantic import BaseModel
from typing import List, Optional, Union
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


class TemplateOptionBase(BaseModel):
    text: str


class TemplateOptionCreate(TemplateOptionBase):
    pass


class TemplateOptionInput(BaseModel):
    text: str
    image_path: Optional[str] = None


class TemplateOptionResponse(BaseModel):
    id: int
    text: str
    image_path: Optional[str] = None

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    title: str
    description: Optional[str] = None
    can_be_public: bool = False
    options: List[Union[TemplateOptionInput, str]]


class TemplateResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    can_be_public: bool
    created_by: int
    options: List[TemplateOptionResponse] = []

    class Config:
        from_attributes = True


class AdminTemplateReviewResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    can_be_public: bool
    is_publish: bool
    created_by: int
    creator_username: str
    options: List[TemplateOptionResponse] = []

    class Config:
        from_attributes = True

class PollFromTemplateRequest(BaseModel):
    title: Optional[str] = None
    options: Optional[List[str]] = None
    duration_seconds: int = 180