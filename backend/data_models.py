from pydantic import BaseModel, Field
from typing import Literal, Optional


class room(BaseModel):
    room_id: str = Field(
        min_length=6,
        max_length=15
    )
    action: Literal["create", "join"]


class upload_file(BaseModel):
    room_id: str = Field(
        min_length=6,
        max_length=15
    )
    session_token: str = Field(
        min_length=1
    )
    filename: str = Field(
        min_length=1,
        max_length=255
    )
    content_type: str = Field(
        min_length=1
    )
    file_data: str = Field(
        min_length=1
    )


class session_request(BaseModel):
    session_token: str = Field(
        min_length=1
    )


class room_history(BaseModel):
    room_id: str = Field(
        min_length=6,
        max_length=15
    )
    session_token: str = Field(
        min_length=1
    )


class room_out(BaseModel):
    room_id: str = Field(
        min_length=6,
        max_length=15
    )
    session_token: str = Field(
        min_length=1
    )


class delete_message(BaseModel):
    message_id: str = Field(
        min_length=1
    )
    session_token: str = Field(
        min_length=1
    )