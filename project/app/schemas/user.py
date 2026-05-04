from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PollOptionResponse(BaseModel):
    id: int
    name: str
    rating_count: int
    total_rating: int
    user_rating: Optional[int] = 0
    image_filename: Optional[str] = None


class PollResponse(BaseModel):
    id: int
    title: str
    duration_seconds: int
    start_time: int
    voting_mode: str = "stars"
    options: List[PollOptionResponse]


class SessionJoinRequest(BaseModel):
    code: str


class OptionWithImage(BaseModel):
    text: str
    image_filename: Optional[str] = None


class SessionCreateRequest(BaseModel):
    template_id: Optional[int] = None
    duration_seconds: int = 180
    options: Optional[List[str]] = None
    options_with_images: Optional[List[OptionWithImage]] = None
    voting_mode: str = "stars"


class SessionCreateResponse(BaseModel):
    token: str
    code: str
    host: str


class SessionStatusResponse(BaseModel):
    token: str
    host: str
    status: str
    poll: Optional[PollResponse] = None
    code: Optional[str] = None
    image_base64: Optional[str] = None

    class Config:
        from_attributes = True