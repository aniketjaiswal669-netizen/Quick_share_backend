from backend import db,random_generation
from datetime import datetime
from fastapi import HTTPException,UploadFile,Form
from bson import ObjectId
from fastapi.responses import Response
import base64


ALLOWED_TYPES = {
    "image/jpeg": 5 * 1024 * 1024,
    "image/png": 5 * 1024 * 1024,
    "image/webp": 5 * 1024 * 1024,

    "application/pdf": 10 * 1024 * 1024,

    "video/mp4": 100 * 1024 * 1024,
}



def room(room_id, action):

    existing_room = db.rooms_collection.find_one({
        "room_id": room_id
    })

    action = action.lower()

    if action == "create":

        if existing_room is not None:
            raise HTTPException(
                status_code=400,
                detail="Room already exists"
            )

        user_name = random_generation.random_user_name(room_id)
        session_token = random_generation.random_session_token()
        now = datetime.now().isoformat()

        room_data = {
            "room_id": room_id,
            "created_by": user_name,
            "created_at": now,
        }

        db.rooms_collection.insert_one(room_data)

        user_data = {
            "room_id": room_id,
            "user_name": user_name,
            "session_token": session_token,
            "joined_at": now,
            "user_type": "admin",
            "status": "online"
        }

        db.user_collection.insert_one(user_data)

        return {
            "message": "Room created successfully",
            "room_id": room_id,
            "user_name": user_name,
            "session_token": session_token
        }

    elif action == "join":

        if existing_room is None:
            raise HTTPException(
                status_code=404,
                detail="Room does not exist"
            )

        user_name = random_generation.random_user_name(room_id)
        session_token = random_generation.random_session_token()
        now = datetime.now().isoformat()

        user_data = {
            "room_id": room_id,
            "user_name": user_name,
            "session_token": session_token,
            "joined_at": now,
            "user_type": "user",
            "status": "online"
        }

        db.user_collection.insert_one(user_data)

        return {
            "message": "Room joined successfully",
            "room_id": room_id,
            "user_name": user_name,
            "session_token": session_token
        }

    else:
        raise HTTPException(
            status_code=400,
            detail="Action must be either 'create' or 'join'"
        )



async def upload_file(
    room_id,
    session_token,
    filename,
    content_type,
    file_data
):
    user = db.user_collection.find_one({
        "room_id": room_id,
        "session_token": session_token
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid session token"
        )

    try:
        file_bytes = base64.b64decode(file_data)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid Base64 file"
        )

    file_document = {
        "room_id": room_id,
        "user_name": user["user_name"],
        "filename": filename,
        "content_type": content_type,
        "size": len(file_bytes),
        "file_data": file_bytes,
        "created_at": datetime.utcnow()
    }

    result = db.files_collection.insert_one(file_document)

    return {
        "message": "File uploaded successfully",
        "file_id": str(result.inserted_id),
        "filename": filename,
        "content_type": content_type,
        "size": len(file_bytes)
    }



def get_messages(room_id, session_token):

    user = db.user_collection.find_one({
        "room_id": room_id,
        "session_token": session_token
    })

    if user is None:
        return {
            "message": "Invalid session"
        }
    
    messages = db.messages_collection.find(
        {
            "room_id": room_id
        },
        {
            "_id": 1,
            "room_id": 1,
            "user_name": 1,
            "message": 1,
            "file_id":1,
            "sent_at": 1
        }
    ).sort("sent_at", 1)

    message_list = []

    for message in messages:
      message["_id"] = str(message["_id"])
      message_list.append(message)

    return {
      "room_id": room_id,
      "messages": message_list
    }



def get_file(file_id: str, session_token: str):
    try:
        file = db.files_collection.find_one({
            "_id": ObjectId(file_id)
        })
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid file ID"
        )

    if not file:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    user = db.user_collection.find_one({
        "room_id": file["room_id"],
        "session_token": session_token
    })

    if not user:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this room"
        )

    file_bytes = bytes(file["file_data"])

    return Response(
        content=file_bytes,
        media_type=file["content_type"],
        headers={
            "Content-Disposition":
                f'inline; filename="{file["filename"]}"'
        }
    )

def room_out(room_id, session_token):

    user = db.user_collection.find_one({
        "room_id": room_id,
        "session_token": session_token
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid room ID or session token"
        )
    
    if user["user_type"] == "admin":

        room = db.rooms_collection.find_one({
            "room_id": room_id
        })

        if not room:
            raise HTTPException(
                status_code=404,
                detail="Room not found"
            )

        db.files_collection.delete_many({
            "room_id": room_id
        })
        db.user_collection.delete_many({
            "room_id": room_id
        })
        db.messages_collection.delete_many({
            "room_id": room_id
        })

        db.rooms_collection.delete_one({
            "room_id": room_id
        })

        return {
            "message": "Chat ended and room deleted",
            "room_id": room_id
        }

    db.user_collection.delete_one({
        "_id": user["_id"]
    })

    return {
        "message": "You have left the room",
        "room_id": room_id
    }




def delete_message(message_id: str, session_token: str):

    user = db.user_collection.find_one({
        "session_token": session_token
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid session token"
        )

    try:
        message_object_id = ObjectId(message_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid message ID"
        )

    message = db.messages_collection.find_one({
        "_id": message_object_id
    })

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )
    if message["room_id"] != user["room_id"]:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete a message from another room"
        )


    if user.get("user_type") == "admin":
        allowed = True

    elif message["user_name"] == user["user_name"]:
        allowed = True

    else:
        allowed = False

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You can delete only your own messages"
        )

    file_id = message.get("file_id")

    if file_id:
        try:
            db.files_collection.delete_one({
                "_id": ObjectId(file_id)
            })
        except Exception:
            pass

    result = db.messages_collection.delete_one({
        "_id": message_object_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Message could not be deleted"
        )

    return {
        "message": "Message deleted successfully",
        "message_id": message_id
    }


def get_active_users(session_token: str):

    user = db.user_collection.find_one({
        "session_token": session_token
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid session token"
        )

    room_id = user["room_id"]

    users = list(db.user_collection.find(
        {"room_id": room_id},
        {
            "_id": 0,
            "user_name": 1,
            "user_type": 1,
            "joined_at": 1
        }
    ))

    return {
        "room_id": room_id,
        "active_users": users,
        "count": len(users)
    }


