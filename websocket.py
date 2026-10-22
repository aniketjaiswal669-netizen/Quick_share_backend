import asyncio
import json

import websockets
from websockets.exceptions import ConnectionClosed

import db

from websocket_function import (
    authenticate,
    add_client,
    remove_client,
    broadcast_active_users,
    handle_chat_message,
    delete_message_event,
    handle_screen_share_request,
    handle_screen_share_response,
    handle_webrtc_offer,
    handle_webrtc_answer,
    handle_ice_candidate,
    handle_screen_share_stop,
    utc_now,
    rooms,
)


async def handle_client(websocket):

    print("\n[WEBSOCKET] New connection attempt...")

    user, session_token = await authenticate(websocket)

    if not user:
        print("[AUTH FAILED] User authentication failed.")
        return

    room_id = user.get("room_id")
    user_name = user.get("user_name")
    user_type = user.get("user_type")

    print("=" * 50)
    print("[USER JOINED]")
    print(f"Username : {user_name}")
    print(f"Room ID  : {room_id}")
    print(f"Role     : {user_type}")
    print(f"Time     : {utc_now()}")
    print("=" * 50)

    websocket.user_data = {
        "room_id": room_id,
        "user_name": user_name,
        "user_type": user_type,
    }

    add_client(room_id, websocket)

    print(f"[CONNECTED] {user_name} added to active clients in room {room_id}")

    try:

        await websocket.send(
            json.dumps({
                "type": "connection",
                "room_id": room_id,
                "user_name": user_name,
                "user_type": user_type,
            })
        )

        print(f"[CONNECTION EVENT] Sent to {user_name}")

        await broadcast_active_users(room_id)
        print(f"[ACTIVE USERS] Broadcast updated for room {room_id}")

        async for raw_message in websocket:

            try:
                data = json.loads(raw_message)

            except json.JSONDecodeError:

                print(f"[INVALID JSON] Received from {user_name}")

                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))

                continue

            event_type = data.get("type")

            print(
                f"[EVENT RECEIVED] User={user_name} | "
                f"Room={room_id} | Type={event_type}"
            )

            if event_type == "screen_share_request":

                print(f"[SCREEN SHARE] Request from {user_name}")

                await handle_screen_share_request(
                    websocket, room_id, user_name, data
                )

            elif event_type == "screen_share_response":

                error = await handle_screen_share_response(
                    room_id, user_name, data
                )

                if error:
                    await websocket.send(json.dumps(error))

            elif event_type == "webrtc_offer":

                print(f"[WEBRTC] Offer from {user_name}")

                error = await handle_webrtc_offer(
                    room_id, user_name, data
                )

                if error:
                    await websocket.send(json.dumps(error))

            elif event_type == "webrtc_answer":

                error = await handle_webrtc_answer(
                    room_id, user_name, data
                )

                if error:
                    await websocket.send(json.dumps(error))

            elif event_type == "ice_candidate":

                error = await handle_ice_candidate(
                    room_id, user_name, data
                )

                if error:
                    await websocket.send(json.dumps(error))

            elif event_type == "screen_share_stop":

                print(f"[SCREEN SHARE] Stopped by {user_name}")

                await handle_screen_share_stop(
                    room_id, websocket, user_name
                )

            elif event_type == "delete_message":

                message_id = data.get("message_id")

                print(
                    f"[DELETE MESSAGE] User={user_name} | "
                    f"Message ID={message_id}"
                )

                if not message_id:
                    await websocket.send(json.dumps({
                        "type": "delete_message_error",
                        "message": "message_id is required"
                    }))
                    continue

                result = await delete_message_event(
                    room_id,
                    message_id,
                    session_token
                )

                if result and result.get("type") == "delete_message_error":
                    print(f"[DELETE FAILED] {result.get('message')}")
                    await websocket.send(json.dumps(result))
                else:
                    print(f"[DELETE PROCESSED] Message ID={message_id}")

            elif event_type == "message":

                print(f"[CHAT MESSAGE] Received from {user_name}")

                error = await handle_chat_message(
                    room_id,
                    user_name,
                    data
                )

                if error:
                    await websocket.send(json.dumps(error))

            else:
                print(f"[UNKNOWN EVENT] {event_type} from {user_name}")

                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Unknown event type"
                }))

    except ConnectionClosed:

        print(
            f"\n[DISCONNECTED] {user_name} left room {room_id} "
            f"at {utc_now()}"
        )

    except Exception as e:

        print(f"[WEBSOCKET ERROR] User={user_name} | Error={e}")


    finally:
        print(f"[CLEANUP STARTED] User={user_name} | Room={room_id}")

        remove_client(room_id, websocket)

        db.user_collection.update_one(
            {
                "room_id": room_id,
                "session_token": session_token
            },
            {
                "$set": {
                    "left_at": utc_now(),
                    "status": "offline"
                }
            }
        )

        print(f"[USER STATUS UPDATED] {user_name} marked as left")

        if user_type == "admin":

            print(f"[ADMIN DISCONNECTED] Finding replacement for {user_name}")

            # Demote the disconnected admin
            db.user_collection.update_one(
                {
                    "room_id": room_id,
                    "session_token": session_token
                },
                {
                    "$set": {"user_type": "user"}
                }
            )
            
            all_users = list(
               db.user_collection.find(
                   {"room_id": room_id},
                   {
                       "_id": 0,
                       "user_name": 1,
                       "user_type": 1,
                       "session_token": 1,
                       "left_at": 1,
                       "status": 1,
                       "joined_at": 1
                   }
               )
            )

            print(f"[DEBUG] Users found in room: {len(all_users)}")
           

            print(f"[OLD ADMIN DEMOTED] {user_name}")

            # Find the earliest active user
            user_list = db.user_collection.find_one(
                {
                    "room_id": room_id,
                    "session_token": {"$ne": session_token},
                    "left_at": "",
                    "status": "online"
                },
                sort=[("joined_at", 1)]
            )
            next_admin=user_list[0]
            print(next_admin["user_name"])
            if next_admin:
                next_admin_username = next_admin["user_name"]
                result = db.user_collection.update_one(
                    {
                        "room_id": room_id,
                        "user_name":next_admin_username
                    },
                    {
                        "$set": {"user_type": "admin"}
                    }
                )

                print(
                    f"[ADMIN UPDATE] Matched={result.matched_count} | "
                    f"Modified={result.modified_count}"
                )

                promoted_user = db.user_collection.find_one(
                    {"_id": next_admin["_id"]},
                    {
                        "_id": 0,
                        "user_name": 1,
                        "user_type": 1,
                        "status": 1,
                        "left_at": 1
                    }
                )

                print(f"[ADMIN VERIFY] {promoted_user}")

            else:
                print(f"[NO REPLACEMENT] No active users in room {room_id}")

        if room_id in rooms:
            await broadcast_active_users(room_id)
            print(f"[ACTIVE USERS] Final update broadcast for room {room_id}")

        print(f"[CLEANUP COMPLETE] {user_name} | Room={room_id}")
        print("=" * 50)


async def main():

    print("WebSocket server running on " "0.0.0.0:8001")

    async with websockets.serve(handle_client, "0.0.0.0", 8001):

        await asyncio.Future()


if __name__ == "__main__":

    asyncio.run(main())
