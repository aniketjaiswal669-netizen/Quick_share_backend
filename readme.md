
Library
/
README.md



Quick Share Backend
FastAPI + MongoDB + WebSocket backend for the Quick Share room-based chat and file-sharing application.

Current Features
Create and join rooms

Session-token authentication

Admin and normal-user roles

Real-time text messaging through WebSocket

File sharing through REST upload + WebSocket file notifications

Files stored directly in MongoDB as BSON Binary

MongoDB _id used as file_id and message ID

Message history

User/admin message deletion

Protected file download

Active-user tracking

left_at tracking for users who leave

Admin room cleanup

Pydantic validation for room requests

GridFS is not used in the current backend.

Project Structure
Quick_share/
├── backend/
│   ├── main.py
│   ├── router.py
│   ├── db.py
│   ├── data_models.py
│   └── websocket.py
├── venv/
└── README.md
MongoDB Collections
rooms
Stores room information.

{
  "room_id": "III999",
  "created_at": "2026-09-24T14:00:00",
  "last_activity": "2026-09-24T15:03:10"
}
room_users
Stores users, sessions, roles, and leave time.

{
  "room_id": "III999",
  "session_token": "session-token",
  "user_name": "BrightKoala",
  "user_type": "admin",
  "joined_at": "2026-09-24T14:01:00",
  "left_at": null
}
When a normal user leaves, the record is retained and only left_at is updated.

left_at = current UTC time
Active users are users whose:

left_at = null
messages
{
  "_id": "ObjectId(...)",
  "room_id": "III999",
  "user_name": "BrightKoala",
  "message": "Hello everyone",
  "file_id": null,
  "type": "text",
  "sent_at": "2026-09-24T15:03:10"
}
files
{
  "_id": "ObjectId(...)",
  "room_id": "III999",
  "user_name": "BrightKoala",
  "filename": "image.png",
  "content_type": "image/png",
  "size": 50360,
  "file_data": "<BSON Binary>",
  "created_at": "2026-09-24T15:04:00"
}
REST API
Create / Join Room
POST /room
Request:

{
  "room_id": "345678",
  "action": "create"
}
action can be:

create
join
room_id is validated with a minimum length of 4 and maximum length of 15.

Response contains:

{
  "room_id": "345678",
  "session_token": "...",
  "user_name": "GoldenOtter",
  "user_type": "admin"
}
Upload File
POST /upload
Form fields:

room_id
session_token
filename
content_type
file_data
file_data is Base64 encoded.

The backend decodes the Base64 data, stores the bytes as BSON Binary, and MongoDB generates the file_id.

Example response:

{
  "message": "File uploaded successfully",
  "file_id": "66f100000000000000000010",
  "filename": "image.png",
  "content_type": "image/png",
  "size": 50360
}
Get File
GET /file/{file_id}?session_token={session_token}
The backend validates the session, verifies that the user belongs to the same room as the file, and returns the original file bytes and content type.

Message History
GET /history/{room_id}?session_token={session_token}
Returns messages in chronological order.

The MongoDB _id is converted to a string so the frontend can use it for deletion.

Example:

{
  "room_id": "III999",
  "messages": [
    {
      "_id": "66f100000000000000000004",
      "room_id": "III999",
      "user_name": "BrightKoala",
      "message": "Hello everyone",
      "file_id": null,
      "sent_at": "2026-09-24T15:03:10"
    }
  ]
}
Delete Message
DELETE /message/{message_id}?session_token={session_token}
Permissions:

Normal user → can delete own messages
Admin       → can delete any message in the room
If the message contains a file_id, the associated file is also deleted.

No separate message_id database field is required because MongoDB _id is used.

Active Users
GET /room/active-users?session_token={session_token}
All users in the room can access this endpoint.

Example:

{
  "room_id": "III999",
  "active_users": [
    {
      "user_name": "BrightKoala",
      "user_type": "admin",
      "joined_at": "2026-09-24T14:01:00",
      "left_at": null
    }
  ],
  "count": 1
}
Leave / End Room
POST /room/out
Parameters:

room_id
session_token
Normal users are marked as left:

left_at = datetime.utcnow()
Their user record is retained.

Admin room-ending behavior removes the room's associated data according to the current backend cleanup logic.

WebSocket
Connection:

ws://HOST:8001?session_token=YOUR_SESSION_TOKEN
The session token is validated before accepting the connection.

Connection Response
{
  "type": "connection",
  "status": "connected",
  "room_id": "III999",
  "user_name": "BrightKoala"
}
Text Message
{
  "message": "Hello everyone"
}
File Message
First upload the file through /upload, then send the returned file_id:

{
  "file_id": "66f100000000000000000010"
}
Text + File
{
  "message": "Here is the image",
  "file_id": "66f100000000000000000010"
}
Message types:

message only       → text
file only          → file
message + file     → text_file
The WebSocket sends file references and metadata, not the actual file bytes.

User Leave Tracking
The current logic keeps normal users in room_users.

User joins
    ↓
left_at = null
    ↓
User disconnects/leaves
    ↓
left_at = current UTC time
    ↓
User record remains
This allows the database to retain user history while active-user APIs only return users with left_at: null.

Admin Cleanup
When the admin ends/leaves according to the current cleanup logic:

Delete room messages
        ↓
Delete room files
        ↓
Delete room users
        ↓
Delete room
The file cleanup should use:

db.files_collection.delete_many({
    "room_id": room_id
})
Running the Backend
Activate the virtual environment:

source venv/bin/activate
Run FastAPI:

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
FastAPI documentation:

http://localhost:8000/docs
The WebSocket server runs separately on its configured port.

Recommended .gitignore
__pycache__/
*.py[cod]
venv/
.venv/
.env
Do not commit virtual environments, Python cache files, or secrets.

Architecture
React / Vite Frontend
        │
        ├──────── HTTP ────────► FastAPI :8000
        │                          │
        │                          ▼
        │                       MongoDB
        │
        └──── WebSocket ──────► WebSocket server :8001
File flow
Frontend
   │
   │ POST /upload
   │ Base64 file
   ▼
MongoDB files collection
   │
   │ generated file_id
   ▼
WebSocket message
   │
   │ file_id
   ▼
Other clients
   │
   │ GET /file/{file_id}
   ▼
File bytes
Security / Validation
Session tokens are checked for:

File upload

File retrieval

Message history

Message deletion

Active-user requests

Room exit

WebSocket connections

Room-specific resources are also checked against the authenticated user's room.