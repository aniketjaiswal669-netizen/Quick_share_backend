import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

from websockets.exceptions import ConnectionClosed

import db


# ============================================================
# GLOBAL ACTIVE CONNECTIONS
# ============================================================

rooms = {}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_session_token(websocket):
    """
    Extract session_token from WebSocket URL.

    Example:
    ws://192.168.1.100:8001/?session_token=abc123
    """

    query = websocket.request.path

    parsed_url = urlparse(query)

    params = parse_qs(parsed_url.query)

    return params.get("session_token", [None])[0]


def get_user(session_token):
    """
    Get user from MongoDB using session token.
    """

    return db.user_collection.find_one({
        "session_token": session_token
    })


# ============================================================
# AUTHENTICATION
# ============================================================

async def authenticate(websocket):
    """
    Authenticate WebSocket connection using session token.
    """

    session_token = get_session_token(websocket)

    if not session_token:
        await websocket.close(
            code=4001,
            reason="Session token required"
        )
        return None, None

    user = get_user(session_token)

    if not user:
        await websocket.close(
            code=4003,
            reason="Invalid session"
        )
        return None, None

    room_id = user.get("room_id")

    if not room_id:
        await websocket.close(
            code=4004,
            reason="Room not found"
        )
        return None, None

    return user, session_token


# ============================================================
# ROOM / CONNECTION FUNCTIONS
# ============================================================

def add_client(room_id, websocket):
    """
    Add WebSocket connection to a room.
    """

    if room_id not in rooms:
        rooms[room_id] = set()

    rooms[room_id].add(websocket)


def remove_client(room_id, websocket):
    """
    Remove WebSocket connection from a room.
    """

    if room_id not in rooms:
        return

    rooms[room_id].discard(websocket)

    if not rooms[room_id]:
        del rooms[room_id]


def get_active_users(room_id):
    """
    Return currently connected users in a room.
    """

    if room_id not in rooms:
        return []

    active_users = []

    for websocket in rooms[room_id]:

        user = getattr(
            websocket,
            "user_data",
            None
        )

        if user:

            active_users.append({
                "user_name": user.get("user_name"),
                "user_type": user.get("user_type")
            })

    return active_users


# ============================================================
# BROADCAST FUNCTIONS
# ============================================================

async def broadcast_to_room(
    room_id,
    message,
    exclude_websocket=None
):
    """
    Send a message to everyone in a room.

    exclude_websocket:
    Connection that should NOT receive the message.
    """

    if room_id not in rooms:
        return

    disconnected_clients = set()

    clients = list(rooms[room_id])

    for client in clients:

        if client == exclude_websocket:
            continue

        try:

            await client.send(message)

        except ConnectionClosed:

            disconnected_clients.add(client)

        except Exception as e:

            print("Broadcast error:", e)

            disconnected_clients.add(client)

    for client in disconnected_clients:

        if room_id in rooms:
            rooms[room_id].discard(client)

    if room_id in rooms and not rooms[room_id]:
        del rooms[room_id]


async def send_to_user(
    room_id,
    target_user_name,
    message
):
    """
    Send a message to one specific user.
    """

    if room_id not in rooms:
        return False

    clients = list(rooms[room_id])

    for client in clients:

        user_data = getattr(
            client,
            "user_data",
            None
        )

        if not user_data:
            continue

        if user_data.get("user_name") == target_user_name:

            try:

                await client.send(message)

                return True

            except ConnectionClosed:

                remove_client(
                    room_id,
                    client
                )

                return False

            except Exception as e:

                print(
                    "Send to user error:",
                    e
                )

                return False

    return False


async def broadcast_active_users(room_id):
    """
    Send active users list to everyone.
    """

    if room_id not in rooms:
        return

    active_users = get_active_users(room_id)

    response = json.dumps({
        "type": "active_users",
        "count": len(active_users),
        "users": active_users
    })

    await broadcast_to_room(
        room_id,
        response
    )


# ============================================================
# CHAT FUNCTIONS
# ============================================================

async def handle_chat_message(
    room_id,
    user_name,
    data
):
    """
    Store and broadcast a chat message.
    """

    message_text = data.get("message")

    file_id = data.get("file_id")

    if not message_text and not file_id:

        return {
            "type": "error",
            "message": "Message or file_id required"
        }

    if message_text and file_id:

        message_type = "text_file"

    elif message_text:

        message_type = "text"

    else:

        message_type = "file"

    message_data = {

        "room_id": room_id,

        "user_name": user_name,

        "message": message_text,

        "file_id": file_id,

        "type": message_type,

        "created_at": utc_now()
    }

    result = db.messages_collection.insert_one(
        message_data
    )

    message_data["_id"] = str(
        result.inserted_id
    )

    response = json.dumps({

        "type": "message",

        "data": message_data
    })

    await broadcast_to_room(
        room_id,
        response
    )

    return None


async def delete_message_event(
    room_id,
    message_id
):
    """
    Notify all users that a message was deleted.

    Actual MongoDB deletion should be
    handled by the REST API.
    """

    response = json.dumps({

        "type": "message_deleted",

        "message_id": message_id
    })

    await broadcast_to_room(
        room_id,
        response
    )


# ============================================================
# SCREEN SHARE FUNCTIONS
# ============================================================

async def handle_screen_share_request(
    websocket,
    room_id,
    user_name,
    data
):
    """
    Send screen-share request to all other users.
    """

    request_id = data.get("request_id")

    if not request_id:

        await websocket.send(
            json.dumps({
                "type": "error",
                "message": "request_id required"
            })
        )

        return

    response = json.dumps({

        "type": "screen_share_request",

        "request_id": request_id,

        "user_name": user_name
    })

    await broadcast_to_room(
        room_id,
        response,
        exclude_websocket=websocket
    )


async def handle_screen_share_response(
    room_id,
    user_name,
    data
):
    """
    Forward screen-share Accept/Reject response
    to the original requester.

    user_name = user who clicked Accept/Reject
    target_user = original requester
    """

    request_id = data.get("request_id")

    accepted = data.get("accepted")

    target_user = data.get("target_user")

    if not request_id:
        return {
            "type": "error",
            "message": "request_id required"
        }

    if not target_user:
        return {
            "type": "error",
            "message": "target_user required"
        }

    response = json.dumps({
        "type": "screen_share_response",

        # Original request ID
        "request_id": request_id,

        # True = accepted, False = rejected
        "accepted": bool(accepted),

        # Original requester
        "target_user": target_user,

        # User who accepted/rejected
        "user_name": user_name
    })

    sent = await send_to_user(
        room_id,
        target_user,
        response
    )

    if not sent:
        return {
            "type": "error",
            "message": "Target user is not connected"
        }

    return None
# ============================================================
# WEBRTC SIGNALING
# ============================================================

async def handle_webrtc_offer(
    room_id,
    user_name,
    data
):
    """
    Forward WebRTC offer to target user.
    """

    target_user = data.get("target_user")

    offer = data.get("offer")

    if not target_user:

        return {
            "type": "error",
            "message": "target_user required"
        }

    if not offer:

        return {
            "type": "error",
            "message": "offer required"
        }

    response = json.dumps({

        "type": "webrtc_offer",

        "from_user": user_name,

        "offer": offer
    })

    sent = await send_to_user(
        room_id,
        target_user,
        response
    )

    if not sent:

        return {
            "type": "error",
            "message": "Target user is not connected"
        }

    return None


async def handle_webrtc_answer(
    room_id,
    user_name,
    data
):
    """
    Forward WebRTC answer to target user.
    """

    target_user = data.get("target_user")

    answer = data.get("answer")

    if not target_user:

        return {
            "type": "error",
            "message": "target_user required"
        }

    if not answer:

        return {
            "type": "error",
            "message": "answer required"
        }

    response = json.dumps({

        "type": "webrtc_answer",

        "from_user": user_name,

        "answer": answer
    })

    sent = await send_to_user(
        room_id,
        target_user,
        response
    )

    if not sent:

        return {
            "type": "error",
            "message": "Target user is not connected"
        }

    return None


async def handle_ice_candidate(
    room_id,
    user_name,
    data
):
    """
    Forward ICE candidate to target user.
    """

    target_user = data.get("target_user")

    candidate = data.get("candidate")

    if not target_user:

        return {
            "type": "error",
            "message": "target_user required"
        }

    if not candidate:

        return {
            "type": "error",
            "message": "candidate required"
        }

    response = json.dumps({

        "type": "ice_candidate",

        "from_user": user_name,

        "candidate": candidate
    })

    sent = await send_to_user(
        room_id,
        target_user,
        response
    )

    if not sent:

        return {
            "type": "error",
            "message": "Target user is not connected"
        }

    return None


async def handle_screen_share_stop(
    room_id,
    websocket,
    user_name
):
    """
    Tell other users that screen sharing stopped.
    """

    response = json.dumps({

        "type": "screen_share_stop",

        "user_name": user_name
    })

    await broadcast_to_room(
        room_id,
        response,
        exclude_websocket=websocket
    )