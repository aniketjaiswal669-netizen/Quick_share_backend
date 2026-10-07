import asyncio
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import websockets
from websockets.exceptions import ConnectionClosed

import db


# ============================================================
# ACTIVE WEBSOCKET CLIENTS
# rooms = {
#     "UIU888": {websocket1, websocket2}
# }
# ============================================================

rooms = {}


# ============================================================
# TIME
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# GET USER FROM SESSION TOKEN
# ============================================================

def get_user(session_token):
    return db.user_collection.find_one({
        "session_token": session_token
    })


# ============================================================
# ADD CLIENT
# ============================================================

def add_client(room_id, websocket):

    if room_id not in rooms:
        rooms[room_id] = set()

    rooms[room_id].add(websocket)


# ============================================================
# REMOVE CLIENT
# ============================================================

def remove_client(room_id, websocket):

    if room_id not in rooms:
        return

    rooms[room_id].discard(websocket)

    if not rooms[room_id]:
        del rooms[room_id]


# ============================================================
# GET ACTIVE USERS
# ============================================================

def get_active_users(room_id):

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
# BROADCAST TO ROOM
# ============================================================

async def broadcast_to_room(room_id, message):

    if room_id not in rooms:
        return

    disconnected_clients = set()

    # Make a copy so the original set cannot cause
    # iteration problems if something disconnects.
    clients = list(rooms[room_id])

    for client in clients:

        try:

            await client.send(message)

        except ConnectionClosed:

            disconnected_clients.add(client)

        except Exception as e:

            print(
                "Broadcast error:",
                e
            )

            disconnected_clients.add(client)

    # Remove disconnected clients
    for client in disconnected_clients:

        if room_id in rooms:
            rooms[room_id].discard(client)

    # Delete empty room from memory
    if room_id in rooms and not rooms[room_id]:

        del rooms[room_id]


# ============================================================
# BROADCAST ACTIVE USERS
# ============================================================

async def broadcast_active_users(room_id):

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
# BROADCAST MESSAGE DELETED
# ============================================================

async def broadcast_message_deleted(
    room_id,
    message_id
):

    response = json.dumps({

        "type": "message_deleted",

        "message_id": message_id

    })

    await broadcast_to_room(
        room_id,
        response
    )


# ============================================================
# HANDLE CLIENT
# ============================================================

async def handle_client(websocket):

    room_id = None
    user = None
    session_token = None
    user_name = None

    try:

        # ----------------------------------------------------
        # GET SESSION TOKEN
        # ----------------------------------------------------

        query = websocket.request.path

        parsed_url = urlparse(query)

        params = parse_qs(
            parsed_url.query
        )

        session_token = params.get(
            "session_token",
            [None]
        )[0]

        if not session_token:

            await websocket.close(
                code=4001,
                reason="Session token required"
            )

            return

        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

        user = get_user(
            session_token
        )

        if not user:

            await websocket.close(
                code=4003,
                reason="Invalid session"
            )

            return

        # ----------------------------------------------------
        # GET USER DETAILS
        # ----------------------------------------------------

        room_id = user.get(
            "room_id"
        )

        user_name = user.get(
            "user_name"
        )

        user_type = user.get(
            "user_type"
        )

        if not room_id:

            await websocket.close(
                code=4004,
                reason="Room not found"
            )

            return

        # ----------------------------------------------------
        # STORE USER DATA ON WEBSOCKET
        # ----------------------------------------------------

        websocket.user_data = {

            "user_name": user_name,

            "user_type": user_type,

            "room_id": room_id,

            "session_token": session_token
        }

        # ----------------------------------------------------
        # ADD CLIENT
        # ----------------------------------------------------

        add_client(
            room_id,
            websocket
        )

        print(
            f"{user_name} connected "
            f"to room {room_id}"
        )

        # ----------------------------------------------------
        # CONNECTION RESPONSE
        # ----------------------------------------------------

        await websocket.send(
            json.dumps({

                "type": "connection",

                "status": "connected",

                "room_id": room_id,

                "user_name": user_name,

                "user_type": user_type

            })
        )

        # ----------------------------------------------------
        # BROADCAST ACTIVE USERS
        # ----------------------------------------------------

        await broadcast_active_users(
            room_id
        )

        # ====================================================
        # RECEIVE MESSAGES
        # ====================================================

        async for raw_message in websocket:

            # ------------------------------------------------
            # PARSE JSON
            # ------------------------------------------------

            try:

                data = json.loads(
                    raw_message
                )

            except json.JSONDecodeError:

                await websocket.send(
                    json.dumps({

                        "type": "error",

                        "message":
                        "Invalid JSON"

                    })
                )

                continue

            # ------------------------------------------------
            # GET EVENT TYPE
            # ------------------------------------------------

            event_type = data.get(
                "type"
            )

            # =================================================
            # DELETE MESSAGE EVENT
            # =================================================

            if event_type == "delete_message":

                message_id = data.get(
                    "message_id"
                )

                if not message_id:

                    await websocket.send(
                        json.dumps({

                            "type": "error",

                            "message":
                            "message_id required"

                        })
                    )

                    continue

                # NOTE:
                # Actual permission checking and MongoDB
                # deletion should be handled by your
                # DELETE API.
                #
                # This WebSocket event only broadcasts
                # the deletion to connected users.

                await broadcast_message_deleted(
                    room_id,
                    message_id
                )

                print(
                    f"Message {message_id} "
                    f"deleted in room {room_id}"
                )

                continue

            # =================================================
            # NORMAL MESSAGE
            # =================================================

            message_text = data.get(
                "message"
            )

            file_id = data.get(
                "file_id"
            )

            # ------------------------------------------------
            # VALIDATE MESSAGE
            # ------------------------------------------------

            if not message_text and not file_id:

                await websocket.send(
                    json.dumps({

                        "type": "error",

                        "message":
                        "Message or file_id required"

                    })
                )

                continue

            # ------------------------------------------------
            # DETERMINE MESSAGE TYPE
            # ------------------------------------------------

            if message_text and file_id:

                message_type = "text_file"

            elif message_text:

                message_type = "text"

            else:

                message_type = "file"

            # ------------------------------------------------
            # CREATE MESSAGE DATA
            # ------------------------------------------------

            message_data = {

                "room_id": room_id,

                "user_name": user_name,

                "message": message_text,

                "file_id": file_id,

                "type": message_type,

                "created_at": utc_now()

            }

            # ------------------------------------------------
            # SAVE TO MONGODB
            # ------------------------------------------------

            result = (
                db.messages_collection.insert_one(
                    message_data
                )
            )

            message_data["_id"] = str(
                result.inserted_id
            )

            # ------------------------------------------------
            # BROADCAST MESSAGE
            # ------------------------------------------------

            response = json.dumps({

                "type": "message",

                "data": message_data

            })

            await broadcast_to_room(
                room_id,
                response
            )

    # ========================================================
    # CONNECTION CLOSED
    # ========================================================

    except ConnectionClosed:

        print(
            f"{user_name or 'User'} "
            f"disconnected"
        )

    # ========================================================
    # OTHER ERRORS
    # ========================================================

    except Exception as e:

        print(
            "WebSocket error:",
            e
        )

    # ========================================================
    # CLEANUP
    # ========================================================

    finally:

        if room_id:

            # ------------------------------------------------
            # REMOVE FROM ACTIVE CLIENTS
            # ------------------------------------------------

            remove_client(
                room_id,
                websocket
            )

            print(
                f"{user_name or 'User'} "
                f"removed from active clients"
            )

            # ------------------------------------------------
            # ADMIN CLEANUP
            # ------------------------------------------------

            if (
                user
                and user.get("user_type") == "admin"
            ):

                # Delete all messages
                db.messages_collection.delete_many({
                    "room_id": room_id
                })

                # Delete all files
                db.files_collection.delete_many({
                    "room_id": room_id
                })

                # Delete all room users
                db.user_collection.delete_many({
                    "room_id": room_id
                })

                # Delete room
                room_result = (
                    db.rooms_collection.delete_one({
                        "room_id": room_id
                    })
                )

                print(
                    "Rooms deleted:",
                    room_result.deleted_count
                )

                print(
                    "========== CLEANUP DONE ==========\n"
                )

            # ------------------------------------------------
            # NORMAL USER LEFT
            # ------------------------------------------------

            else:

                if session_token:

                    db.user_collection.update_one(

                        {
                            "session_token":
                            session_token,

                            "room_id":
                            room_id
                        },

                        {
                            "$set": {
                                "left_at":
                                utc_now()
                            }
                        }

                    )

                    print(
                        f"{user_name} "
                        f"marked as left"
                    )

            # ------------------------------------------------
            # UPDATE ACTIVE USERS
            # ------------------------------------------------

            if room_id in rooms:

                await broadcast_active_users(
                    room_id
                )


# ============================================================
# WEBSOCKET SERVER
# ============================================================

async def main():

    async with websockets.serve(

        handle_client,

        "0.0.0.0",

        8001

    ):

        print(
            "WebSocket server running "
            "on ws://0.0.0.0:8001"
        )

        await asyncio.Future()


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
