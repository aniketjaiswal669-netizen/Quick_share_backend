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

    user, session_token = await authenticate(websocket)

    if not user:
        return

    room_id = user.get("room_id")
    user_name = user.get("user_name")
    user_type = user.get("user_type")

    websocket.user_data = {
        "room_id": room_id,
        "user_name": user_name,
        "user_type": user_type,
    }

    add_client(room_id, websocket)

    try:

        # Send connection information
        await websocket.send(
            json.dumps(
                {
                    "type": "connection",
                    "room_id": room_id,
                    "user_name": user_name,
                    "user_type": user_type,
                }
            )
        )

        await broadcast_active_users(room_id)

        # Listen for messages
        async for raw_message in websocket:

            try:

                data = json.loads(raw_message)

            except json.JSONDecodeError:

                await websocket.send(
                    json.dumps({"type": "error", "message": "Invalid JSON"})
                )

                continue

            event_type = data.get("type")

            # ==================================================
            # SCREEN SHARE REQUEST
            # ==================================================

            if event_type == "screen_share_request":

                await handle_screen_share_request(websocket, room_id, user_name, data)

            # ==================================================
            # SCREEN SHARE RESPONSE
            # ==================================================

            elif event_type == "screen_share_response":

                error = await handle_screen_share_response(room_id, user_name, data)

                if error:
                    await websocket.send(json.dumps(error))

            # ==================================================
            # WEBRTC OFFER
            # ==================================================

            elif event_type == "webrtc_offer":

                error = await handle_webrtc_offer(room_id, user_name, data)

                if error:
                    await websocket.send(json.dumps(error))

            # ==================================================
            # WEBRTC ANSWER
            # ==================================================

            elif event_type == "webrtc_answer":

                error = await handle_webrtc_answer(room_id, user_name, data)

                if error:
                    await websocket.send(json.dumps(error))

            # ==================================================
            # ICE CANDIDATE
            # ==================================================

            elif event_type == "ice_candidate":

                error = await handle_ice_candidate(room_id, user_name, data)

                if error:
                    await websocket.send(json.dumps(error))

            # ==================================================
            # SCREEN SHARE STOP
            # ==================================================

            elif event_type == "screen_share_stop":

                await handle_screen_share_stop(room_id, websocket, user_name)

            # ==================================================
            # MESSAGE DELETE EVENT
            # ==================================================

            elif event_type == "delete_message":

                message_id = data.get("message_id")

                if message_id:

                    await delete_message_event(room_id, message_id)

            # ==================================================
            # NORMAL CHAT MESSAGE
            # ==================================================

            else:

                error = await handle_chat_message(room_id, user_name, data)

                if error:

                    await websocket.send(json.dumps(error))

    except ConnectionClosed:

        print(f"{user_name} disconnected from {room_id}")

    except Exception as e:

        print("WebSocket error:", e)

    finally:
        remove_client(room_id, websocket)

        if user_type == "admin":
            db.rooms_collection.delete_one({"room_id": room_id})

            db.user_collection.delete_many({"room_id": room_id})

            db.messages_collection.delete_many({"room_id": room_id})

            db.files_collection.delete_many({"room_id": room_id})

        else:
            db.user_collection.update_one(
                {"room_id": room_id, "session_token": session_token},
                {"$set": {"left_at": utc_now()}},
            )

    if room_id in rooms:
        await broadcast_active_users(room_id)


async def main():

    print("WebSocket server running on " "0.0.0.0:8001")

    async with websockets.serve(handle_client, "0.0.0.0", 8001):

        await asyncio.Future()


if __name__ == "__main__":

    asyncio.run(main())
