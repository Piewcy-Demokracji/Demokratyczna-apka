from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
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


class SessionJoinRequest(BaseModel):
    code: str


class SessionCreateResponse(BaseModel):
    token: str
    code: str
    host: str


class SessionStatusResponse(BaseModel):
    token: str
    host: str
    status: str
    code: Optional[str] = None

    class Config:
        from_attributes = True
