from pydantic import BaseModel, Field
from typing import Literal, Optional


class room(BaseModel):
    room_id: str = Field(
        min_length=6,
        max_length=15
    )
    action: Literal["create", "join"]



class room_out(BaseModel):
    room_id: str = Field(
        min_length=6,
        max_length=15
    )
    session_token: str = Field(
        min_length=1
    )


class TransferAdminRequest(BaseModel):
    room_id: str
    session_token: str
    user_name: str

class DeleteRoomRequest(BaseModel):
    room_id: str = Field(..., min_length=6, max_length=15)
    session_token: str = Field(..., min_length=1)
