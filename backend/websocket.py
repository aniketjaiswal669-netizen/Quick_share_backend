import json
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed
import db

rooms = {}


def get_user(session_token):

    user = db.user_collection.find_one({
        "session_token": session_token
    })

    return user


def add_client(room_id, websocket):

    if room_id not in rooms:
        rooms[room_id] = set()

    rooms[room_id].add(websocket)



def remove_client(room_id, websocket):

    if room_id not in rooms:
        return
    rooms[room_id].discard(websocket)
    if len(rooms[room_id]) == 0:
        del rooms[room_id]


async def broadcast_to_room(room_id, message):

    if room_id not in rooms:
        return

    disconnected_clients = set()

    for client in rooms[room_id]:

        try:
            await client.send(message)

        except ConnectionClosed:
            disconnected_clients.add(client)

    for client in disconnected_clients:
        rooms[room_id].discard(client)


async def handle_client(websocket):

    room_id = None

    try:

        query = websocket.request.path

        if "?" not in query:
            await websocket.close(
                code=4001,
                reason="Session token required"
            )
            return

        query_string = query.split("?", 1)[1]

        params = {}

        for item in query_string.split("&"):

            if "=" in item:
                key, value = item.split("=", 1)
                params[key] = value

        session_token = params.get("session_token")

        if not session_token:
            await websocket.close(
                code=4001,
                reason="Session token required"
            )
            return



        user = get_user(session_token)

        if not user:

            await websocket.close(
                code=4003,
                reason="Invalid session"
            )

            return


        room_id = user.get("room_id")
        user_name = user.get("user_name")

        if not room_id:

            await websocket.close(
                code=4004,
                reason="Room not found"
            )

            return



        add_client(room_id, websocket)

        print(
            f"{user_name} connected to room {room_id}")

        await websocket.send(
            json.dumps({
                "type": "connection",
                "status": "connected",
                "room_id": room_id,
                "user_name": user_name
            })
        )


        async for raw_message in websocket:

            try:

                data = json.loads(raw_message)

            except json.JSONDecodeError:

                await websocket.send(
                    json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    })
                )

                continue


            message_text = data.get("message")

            file_id = data.get("file_id")



            if not message_text and not file_id:

                await websocket.send(
                    json.dumps({
                        "type": "error",
                        "message":
                        "Message or file_id required"
                    })
                )

                continue


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
                "created_at": datetime.now().isoformat()
            }


            result = db.messages_collection.insert_one(
                message_data
            )



            message_data["_id"] = str(result.inserted_id)

            response = json.dumps({
                "type": "message",
                "data": message_data
            })



            await broadcast_to_room(
                room_id,
                response
            )


    except ConnectionClosed:

        print(
            f"{user_name if 'user_name' in locals() else 'User'} "
            f"disconnected"
        )


    except Exception as e:

        print(
            "WebSocket error:",
            e
        )


    finally:

      if room_id:

        remove_client(
            room_id,
            websocket
        )
        user_type = user.get("user_type") if user else None

        db.user_collection.delete_one({
            "session_token": session_token
        })

        print(
            f"{user_name} removed from user_collection"
        )
        if user_type == "admin":

           db.messages_collection.delete_many({"room_id": room_id})
           db.user_collection.delete_many({"room_id":room_id})
           db.user_collection.find_one({"room_id":room_id})
           room_result = db.rooms_collection.delete_one({"room_id": room_id })
           print("Rooms deleted:",room_result.deleted_count)

           print("========== CLEANUP DONE ==========\n")

async def main():
 
    async with websockets.serve(
        handle_client, 
        "0.0.0.0",
        8001
    ):

        print(
            "WebSocket server running on port 8001"
        )

        await asyncio.Future()


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())





    